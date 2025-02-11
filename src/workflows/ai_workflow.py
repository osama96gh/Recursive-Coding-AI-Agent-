from typing import Dict, Any, Optional, List
import json
import logging
import datetime
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END, START
from pydantic import BaseModel

from src.state.schema import ProjectState, CodeGenerationStatus, ActionDecision, CodeComponent, TestResult

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class AIWorkflowSupervisor:
    """AI-driven workflow supervisor that dynamically controls the development process."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the AI supervisor.
        
        Args:
            llm: The language model to use for decision making and execution
        """
        self.llm = llm
    
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
        
        # Generate decision messages
        messages = [
            SystemMessage(content="You are an AI project manager overseeing a code generation project. You must respond with ONLY a JSON object, no additional text or explanation."),
            HumanMessage(content=f"""Current Context:
{json.dumps(context, indent=2)}

Your task is to decide the next best action. Consider:
1. Project requirements and current progress
2. Code quality and test results
3. Recent actions and their outcomes
4. Whether human input might be needed

Respond with ONLY a JSON object in this format:
{{
    "action_type": "string (e.g., 'analyze', 'generate', 'test', 'refactor', 'ask_human')",
    "description": "string explaining the action",
    "needs_human_input": boolean,
    "human_query": "string (if needs_human_input is true)",
    "context": {{
        "relevant_files": ["list of files to focus on"],
        "specific_focus": "string describing specific aspect to address",
        "expected_outcome": "string describing what this action should achieve"
    }}
}}""")
        ]
        
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract content from AIMessage
            content = response.content if hasattr(response, 'content') else str(response)
            decision_data = json.loads(content)
            return ActionDecision(**decision_data)
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
            result = await self.execute_action(action, state)
            
            # Update state based on result
            return self.update_state_with_result(state, action, result)
            
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
        # Generate appropriate prompt based on action type
        prompt = self.generate_action_prompt(action, state)
        
        # Execute through LLM
        messages = [
            SystemMessage(content="You must respond with ONLY a JSON object, no additional text or explanation."),
            HumanMessage(content=prompt)
        ]
        response = await self.llm.ainvoke(messages)
        
        try:
            # Extract content from AIMessage and parse result
            content = response.content if hasattr(response, 'content') else str(response)
            result = json.loads(content)
            return self.validate_action_result(result, action)
        except Exception as e:
            logger.error(f"Error executing action: {e}")
            return {
                "error": str(e),
                "status": "failed",
                "action_type": action.action_type
            }
    
    def generate_action_prompt(self, action: ActionDecision, state: ProjectState) -> str:
        """Generate an appropriate prompt for the given action.
        
        Args:
            action: The action to generate a prompt for
            state: Current project state
            
        Returns:
            Prompt string for the LLM
        """
        base_context = {
            "requirements": state.original_requirements,
            "current_context": state.current_context,
            "action_context": action.context
        }
        
        prompts = {
            "analyze": f"""Analyze the following project context and provide insights:
{json.dumps(base_context, indent=2)}

You must respond with ONLY a JSON object in the following format, with no additional text or explanation:
{{
    "insights": ["list of key insights"],
    "recommendations": ["list of recommendations"],
    "next_focus": "string describing what to focus on next"
}}""",
            "generate": f"""Generate code based on the following context:
{json.dumps(base_context, indent=2)}

You must respond with ONLY a JSON object in the following format, with no additional text or explanation:
{{
    "file_path": "string",
    "content": "string (the actual code)",
    "language": "string",
    "dependencies": ["list of dependencies"]
}}""",
            "test": f"""Evaluate the following code components:
{json.dumps({
    **base_context,
    "components": state.components
}, indent=2)}

You must respond with ONLY a JSON object in the following format, with no additional text or explanation:
{{
    "test_results": [
        {{
            "component_path": "string",
            "passed": boolean,
            "error_message": "string (if failed)",
            "suggestions": ["list of improvement suggestions"]
        }}
    ]
}}"""
        }
        
        return prompts.get(action.action_type, f"""Execute the following action:
{json.dumps({
    "action": action.dict(),
    "context": base_context
}, indent=2)}

You must respond with ONLY a JSON object containing the results of this action, with no additional text or explanation.""")
    
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
        result["timestamp"] = str(datetime.datetime.now())
        
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
            "result": result,
            "timestamp": result.get("timestamp", str(datetime.datetime.now()))
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
