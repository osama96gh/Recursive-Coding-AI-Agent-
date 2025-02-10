from typing import Dict, List, Optional
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START

from src.state.schema import ProjectState, CodeComponent, TestResult
from src.agents.specialized.requirement_agent import RequirementAnalysisAgent
from src.agents.specialized.code_generation_agent import CodeGenerationAgent
from src.agents.specialized.testing_agent import TestingAgent

class EnhancedRecursiveWorkflow:
    """Enhanced workflow for recursive development using specialized agents."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the enhanced recursive workflow.
        
        Args:
            llm: The language model to use for all agents
        """
        self.requirement_agent = RequirementAnalysisAgent(llm)
        self.code_agent = CodeGenerationAgent(llm)
        self.testing_agent = TestingAgent(llm)
        self.workflow = self._create_workflow()
    
    def _create_workflow(self) -> StateGraph:
        """Create the workflow graph with all nodes and edges.
        
        Returns:
            Compiled StateGraph for execution
        """
        workflow = StateGraph(ProjectState)
        
        # Add nodes for each phase
        workflow.add_node("analyze_requirements", self._analyze_requirements)
        workflow.add_node("generate_code", self._generate_code)
        workflow.add_node("test_code", self._test_code)
        workflow.add_node("refine_code", self._refine_code)
        
        # Define edges with conditions
        workflow.add_edge(START, "analyze_requirements")
        workflow.add_edge("analyze_requirements", "generate_code")
        workflow.add_edge("generate_code", "test_code")
        workflow.add_conditional_edges(
            "test_code",
            self._should_refine,
            {
                True: "refine_code",
                False: END
            }
        )
        workflow.add_edge("refine_code", "generate_code")
        
        return workflow.compile()
    
    async def _analyze_requirements(self, state: ProjectState) -> ProjectState:
        """Analyze and break down requirements into implementable steps.
        
        Args:
            state: Current project state
            
        Returns:
            Updated project state with analyzed requirements
        """
        try:
            requirements = await self.requirement_agent.analyze(state.original_requirements)
            return state.model_copy(update={
                "current_requirements": requirements,
                "status": "analyzing",
                "current_phase": "requirements_analysis"
            })
        except Exception as e:
            return self._handle_error(state, f"Requirements analysis failed: {str(e)}")
    
    async def _generate_code(self, state: ProjectState) -> ProjectState:
        """Generate code components based on current requirements.
        
        Args:
            state: Current project state
            
        Returns:
            Updated project state with generated code
        """
        try:
            new_components: Dict[str, CodeComponent] = {}
            
            for requirement in state.current_requirements:
                component = await self.code_agent.generate(requirement)
                new_components[component.file_path] = component
            
            return state.model_copy(update={
                "components": new_components,
                "status": "generating",
                "current_phase": "code_generation",
                "iteration_count": state.iteration_count + 1
            })
        except Exception as e:
            return self._handle_error(state, f"Code generation failed: {str(e)}")
    
    async def _test_code(self, state: ProjectState) -> ProjectState:
        """Test all generated code components.
        
        Args:
            state: Current project state
            
        Returns:
            Updated project state with test results
        """
        try:
            test_results: Dict[str, List[TestResult]] = {}
            
            for path, component in state.components.items():
                result = await self.testing_agent.test_component(component)
                test_results[path] = [result]
            
            return state.model_copy(update={
                "test_results": test_results,
                "status": "testing",
                "current_phase": "testing"
            })
        except Exception as e:
            return self._handle_error(state, f"Testing failed: {str(e)}")
    
    async def _refine_code(self, state: ProjectState) -> ProjectState:
        """Refine code based on test results.
        
        Args:
            state: Current project state
            
        Returns:
            Updated project state with refinement plans
        """
        try:
            # Identify components that need refinement
            refinement_needed = []
            for path, results in state.test_results.items():
                if not results[-1].passed:
                    refinement_needed.append(path)
            
            if refinement_needed:
                return state.model_copy(update={
                    "status": "refining",
                    "current_phase": "refinement",
                    "next_steps": [f"Refine component: {path}" for path in refinement_needed]
                })
            
            return state.model_copy(update={
                "status": "complete",
                "current_phase": "completed"
            })
        except Exception as e:
            return self._handle_error(state, f"Refinement planning failed: {str(e)}")
    
    def _should_refine(self, state: ProjectState) -> bool:
        """Determine if code needs refinement based on test results and iteration count.
        
        Args:
            state: Current project state
            
        Returns:
            True if refinement is needed, False otherwise
        """
        # Check if we've hit the maximum iterations
        if state.iteration_count >= state.max_iterations:
            return False
        
        # Check if any tests failed
        for results in state.test_results.values():
            if not results[-1].passed:
                return True
        
        return False
    
    def _handle_error(self, state: ProjectState, error_message: str) -> ProjectState:
        """Handle errors by updating state with error information.
        
        Args:
            state: Current project state
            error_message: Error message to log
            
        Returns:
            Updated project state with error information
        """
        return state.model_copy(update={
            "status": "error",
            "error_log": state.error_log + [error_message]
        })
