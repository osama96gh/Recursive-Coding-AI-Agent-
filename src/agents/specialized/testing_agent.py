from typing import Optional, Dict
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.state.schema import CodeComponent, TestResult

class TestingAgent:
    """Agent responsible for testing code components and providing test results."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the TestingAgent.
        
        Args:
            llm: The language model to use for test generation and analysis
        """
        self.llm = llm
        self.output_parser = JsonOutputParser()
        self.test_generation_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert test engineer. Generate comprehensive tests for code components.
            Consider:
            - Edge cases and error conditions
            - Input validation
            - Performance considerations
            - Code coverage
            
            Format your response as a JSON object with:
            {
                "test_code": "generated test code",
                "test_cases": ["list", "of", "test", "cases"],
                "setup_requirements": ["any", "special", "setup", "needed"]
            }"""),
            ("human", """Generate tests for the following code:
            Language: {language}
            Code:
            {code}""")
        ])
    
    async def test_component(self, component: CodeComponent, context: Optional[Dict] = None) -> TestResult:
        """Test a code component and return results.
        
        Args:
            component: The CodeComponent to test
            context: Optional context about the project/testing environment
            
        Returns:
            TestResult containing the test execution results
        """
        try:
            # Generate tests
            test_plan = await self._generate_tests(component)
            
            # Execute tests
            return await self._run_tests(component, test_plan, context)
        except Exception as e:
            return TestResult(
                component_path=component.file_path,
                status="error",
                passed=False,
                error_message=str(e),
                execution_time=0.0
            )
    
    async def _generate_tests(self, component: CodeComponent) -> Dict:
        """Generate tests for a code component.
        
        Args:
            component: The CodeComponent to generate tests for
            
        Returns:
            Dictionary containing generated tests and requirements
        """
        chain = self.test_generation_prompt | self.llm | self.output_parser
        result = await chain.ainvoke({
            "language": component.language,
            "code": component.content
        })
        return result
    
    async def _run_tests(self, component: CodeComponent, test_plan: Dict, context: Optional[Dict] = None) -> TestResult:
        """Execute tests for a code component.
        
        Args:
            component: The CodeComponent being tested
            test_plan: The generated test plan
            context: Optional context about the testing environment
            
        Returns:
            TestResult containing the execution results
        """
        # TODO: Implement actual test execution logic
        # For now, return a placeholder result
        return TestResult(
            component_path=component.file_path,
            status="completed",
            passed=True,  # This should be based on actual test execution
            execution_time=0.0  # This should be actual execution time
        )
    
    def _validate_test_results(self, results: TestResult) -> bool:
        """Validate test results for consistency and completeness.
        
        Args:
            results: The TestResult to validate
            
        Returns:
            True if results are valid, False otherwise
        """
        return (
            results.component_path and
            results.status in ["completed", "error"] and
            isinstance(results.passed, bool) and
            results.execution_time >= 0
        )
