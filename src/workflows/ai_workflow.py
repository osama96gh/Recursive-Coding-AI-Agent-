from typing import Dict, Any, Optional, List
import json
import logging
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from pydantic import BaseModel

from src.state.schema import (
    ProjectState, 
    CodeGenerationStatus, 
    ActionDecision, 
    CodeComponent, 
    TestResult,
    EnhancedActionResult,
    CodeAnalysisOutput
)
from src.agents.tools.output_validator import OutputValidator
from src.agents.tools.prompt_generator import StructuredPromptGenerator

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
logger.addHandler(console_handler)

class AIWorkflowSupervisor:
    """AI-driven workflow supervisor that dynamically controls the development process."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the AI supervisor.
        
        Args:
            llm: The language model to use for decision making and execution
        """
        self.llm = llm
        self.output_validator = OutputValidator()
        self.prompt_generator = StructuredPromptGenerator()
    
    async def decide_next_action(self, state: ProjectState) -> ActionDecision:
        """Determine the next action based on current project state.
        
        Args:
            state: Current project state
            
        Returns:
            ActionDecision containing the next action to take
        """
        # Prepare context for decision-making
        context = {
            "requirements": state.original_requirements,
            "current_context": state.current_context,
            "components": [
                {
                    "path": path,
                    "language": comp.language,
                    "status": comp.status,
                    "version": comp.version
                }
                for path, comp in state.components.items()
            ],
            "test_results": [
                {
                    "component": path,
                    "passed": results[-1].passed if results else False,
                    "suggestions": results[-1].suggestions if results else []
                }
                for path, results in state.test_results.items()
            ],
            "step_count": state.step_count,
            "recent_actions": [
                str(action)  # Now uses our custom __str__ implementation
                for action in state.action_history[-3:]  # Last 3 actions for context
            ] if state.action_history else []
        }
        
        # Generate decision prompt with enhanced instructions
        prompt = self.prompt_generator.generate_prompt(
            "analyze",  # Use analyze type for decision making
            context,
            additional_instructions="""
Consider:
1. Project requirements and current progress
2. Code quality and test results
3. Recent actions and their outcomes
4. Whether human input might be needed

Your response must include:
1. Insights about the current state
2. Recommendations for next steps
3. Code quality metrics if applicable
4. Priority actions to take

Also include a "decision" object in the metadata with this structure:
{
    "action_type": "string (e.g., 'analyze', 'generate', 'test', 'refactor', 'ask_human')",
    "description": "string explaining the action",
    "needs_human_input": boolean,
    "human_query": "string (if needs_human_input is true)",
    "context": {
        "relevant_files": ["list of files to focus on"],
        "specific_focus": "string describing specific aspect to address",
        "expected_outcome": "string describing what this action should achieve"
    }
}"""
        )
        
        messages = [
            SystemMessage(content="You are an AI project manager overseeing a code generation project."),
            HumanMessage(content=prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract content and validate
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Raw LLM response for decision making:\n{content}")
            
            validated_result = await self.output_validator.validate_and_parse(
                content,
                "analyze",
                context={"decision_making": True}
            )
            logger.info(f"Validated decision result:\n{json.dumps(validated_result.dict(), indent=2)}")
            
            # Try to extract decision data from different places
            decision_data = None
            logger.info("Attempting to extract decision data...")
            
            # First try metadata
            if validated_result.output.metadata.get("decision"):
                logger.info("Found decision data in metadata")
                decision_data = validated_result.output.metadata["decision"]
            
            # If not in metadata, try to construct from analysis output
            elif isinstance(validated_result.output, CodeAnalysisOutput):
                logger.info("Constructing decision data from analysis output")
                insights = validated_result.output.insights
                recommendations = validated_result.output.recommendations
                priority_actions = validated_result.output.priority_actions
                
                if priority_actions:
                    first_action = priority_actions[0]
                    # Determine action type from the content
                    action_type = "generate" if any(word in first_action.lower() for word in ["implement", "create", "build", "generate"]) else "analyze"
                    
                    decision_data = {
                        "action_type": action_type,
                        "description": first_action,
                        "needs_human_input": False,
                        "context": {
                            "relevant_files": [],  # Will be populated based on context
                            "specific_focus": first_action,
                            "expected_outcome": recommendations[0] if recommendations else "Improve code quality",
                            "insights": insights,
                            "recommendations": recommendations
                        }
                    }
            
            if decision_data:
                return ActionDecision(**decision_data)
            else:
                raise ValueError("Could not extract or construct valid decision data")
            
        except Exception as e:
            logger.error(f"Error parsing AI decision: {e}")
            # Return a safe default decision
            return ActionDecision(
                action_type="analyze",
                description="Analyzing current state due to decision parsing error",
                needs_human_input=True,
                human_query="There was an error in the AI's decision making. Would you like to provide guidance on the next step?",
                context={"error": str(e)}
            )
    
    async def execute_step(self, state: ProjectState) -> ProjectState:
        """Execute a single step in the AI-controlled workflow.
        
        Args:
            state: Current project state
            
        Returns:
            Updated project state
        """
        try:
            # Check if we've hit the step limit
            if state.step_count >= state.max_steps:
                return state.model_copy(update={
                    "status": CodeGenerationStatus.COMPLETE,
                    "error_log": state.error_log + ["Maximum steps reached"]
                })
            
            # If we have human feedback, incorporate it into the context
            if state.human_feedback:
                state.current_context["human_feedback"] = state.human_feedback
                state.human_feedback = None  # Clear after using
            
            # Get next action
            action = await self.decide_next_action(state)
            
            # Update state with the decision
            state = state.model_copy(update={
                "current_action": action,
                "action_history": state.action_history + [action],
                "step_count": state.step_count + 1
            })
            
            # If we need human input, update state and return
            if action.needs_human_input:
                return state.model_copy(update={
                    "status": CodeGenerationStatus.NEEDS_HUMAN_INPUT,
                    "needs_human_input": True,
                    "human_query": action.human_query
                })
            
            # Execute the action
            logger.info(f"Executing action: {action.action_type} - {action.description}")
            result = await self.execute_action(action, state)
            logger.info(f"Action result:\n{json.dumps(result, indent=2)}")
            
            # Update state based on result
            updated_state = self.update_state_with_result(state, action, result)
            logger.info(f"Updated state status: {updated_state.status}")
            return updated_state
            
        except Exception as e:
            logger.error(f"Error in execute_step: {e}")
            return state.model_copy(update={
                "status": CodeGenerationStatus.ERROR,
                "error_log": state.error_log + [f"Step execution error: {str(e)}"]
            })
    
    async def execute_action(self, action: ActionDecision, state: ProjectState) -> Dict[str, Any]:
        """Execute a specific action using the LLM.
        
        Args:
            action: The action to execute
            state: Current project state
            
        Returns:
            Dictionary containing the result of the action
        """
        # Generate appropriate prompt using StructuredPromptGenerator
        prompt = self.prompt_generator.generate_prompt(
            action.action_type,
            {
                "action": action.dict(),
                "state": state.dict(),
                "context": state.current_context
            }
        )
        
        # Execute through LLM
        messages = [
            SystemMessage(content="You must respond with ONLY a JSON object, no additional text or explanation."),
            HumanMessage(content=prompt)
        ]
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract content and validate using OutputValidator
            content = response.content if hasattr(response, 'content') else str(response)
            logger.info(f"Raw LLM response for action {action.action_type}:\n{content}")
            
            validated_result = await self.output_validator.validate_and_parse(
                content,
                action.action_type,
                context=action.context
            )
            logger.info(f"Validated action result:\n{json.dumps(validated_result.dict(), indent=2)}")
            
            # Return the validated result
            return validated_result.dict()
            
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            # Try to repair malformed output
            try:
                repaired_output = await self.output_validator.repair_malformed_output(
                    content,
                    action.action_type,
                    self._get_expected_schema(action.action_type)
                )
                # Validate and return repaired output
                validated_result = await self.output_validator.validate_and_parse(
                    repaired_output,
                    action.action_type,
                    context=action.context
                )
                return validated_result.dict()
            except Exception as repair_error:
                logger.error(f"Error repairing output: {repair_error}")
                return {
                    "error": str(e),
                    "status": "failed",
                    "action_type": action.action_type
                }
    
    def _get_expected_schema(self, action_type: str) -> Dict[str, Any]:
        """Get the expected schema for a given action type."""
        if action_type == "analyze":
            return {
                "insights": ["string"],
                "recommendations": ["string"],
                "code_quality_metrics": {
                    "complexity": "float",
                    "maintainability": "float",
                    "documentation": "float"
                },
                "priority_actions": ["string"]
            }
        elif action_type == "generate":
            return {
                "file_path": "string",
                "content": "string",
                "language": "string",
                "dependencies": ["string"],
                "quality_checks": {
                    "syntax_valid": "boolean",
                    "follows_style_guide": "boolean",
                    "has_documentation": "boolean"
                }
            }
        elif action_type == "test":
            return {
                "test_cases": [{
                    "name": "string",
                    "status": "string",
                    "error_message": "string (optional)"
                }],
                "coverage": {
                    "line_coverage": "float",
                    "branch_coverage": "float"
                }
            }
        else:
            return {}
    
    def validate_action_result(self, result: Dict[str, Any], action: ActionDecision) -> Dict[str, Any]:
        """Validate and process the result of an action.
        
        Args:
            result: Raw result from LLM
            action: The action that was executed
            
        Returns:
            Validated and processed result
        """
        # Add metadata to result
        result["action_type"] = action.action_type
        
        # Validate based on action type
        if action.action_type == "generate" and "file_path" not in result:
            raise ValueError("Code generation result must include file_path")
        elif action.action_type == "test" and "test_results" not in result:
            raise ValueError("Test result must include test_results array")
            
        return result
    
    def update_state_with_result(
        self, state: ProjectState, action: ActionDecision, result: Dict[str, Any]
    ) -> ProjectState:
        """Update the project state based on an action's result.
        
        Args:
            state: Current project state
            action: The action that was executed
            result: Result of the action
            
        Returns:
            Updated project state
        """
        updates = {
            "status": CodeGenerationStatus.IN_PROGRESS,
            "current_context": {
                **state.current_context,
                f"last_{action.action_type}_result": result
            }
        }
        
        # Handle specific action types
        if action.action_type == "generate" and "error" not in result:
            new_component = CodeComponent(
                file_path=result["file_path"],
                content=result["content"],
                language=result["language"],
                dependencies=result.get("dependencies", [])
            )
            updates["components"] = {
                **state.components,
                result["file_path"]: new_component
            }
        elif action.action_type == "test" and "error" not in result:
            new_test_results = {}
            for test_result in result["test_results"]:
                path = test_result["component_path"]
                new_result = TestResult(
                    component_path=path,
                    status="completed",
                    passed=test_result["passed"],
                    error_message=test_result.get("error_message"),
                    execution_time=0.0,  # TODO: Add actual timing
                    suggestions=test_result.get("suggestions", [])
                )
                existing_results = state.test_results.get(path, [])
                new_test_results[path] = existing_results + [new_result]
            updates["test_results"] = new_test_results
        
        # Add to development history
        history_entry = {
            "step": state.step_count,
            "action": action.dict(),
            "result": result
        }
        updates["development_history"] = state.development_history + [history_entry]
        
        return state.model_copy(update=updates)

class AIControlledWorkflow:
    """Main workflow class implementing AI-controlled development process."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the AI-controlled workflow.
        
        Args:
            llm: The language model to use
        """
        self.ai_supervisor = AIWorkflowSupervisor(llm)
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph.
        
        Returns:
            Compiled StateGraph for execution
        """
        workflow = StateGraph(ProjectState)
        
        # Add the main execution node
        workflow.add_node("execute_step", self.ai_supervisor.execute_step)
        
        # Add edges
        workflow.add_edge(START, "execute_step")
        
        # Add conditional edges based on state
        workflow.add_conditional_edges(
            "execute_step",
            self._get_next_node,
            {
                "continue": "execute_step",
                "complete": END
            }
        )
        
        return workflow.compile()
    
    def _get_next_node(self, state: ProjectState) -> str:
        """Determine whether to continue or end the workflow.
        
        Args:
            state: Current project state
            
        Returns:
            'continue' or 'complete'
        """
        if state.status in [CodeGenerationStatus.COMPLETE, CodeGenerationStatus.ERROR]:
            return "complete"
        return "continue"
