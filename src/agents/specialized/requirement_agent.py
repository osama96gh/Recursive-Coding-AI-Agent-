from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser

class RequirementAnalysisAgent:
    """Agent responsible for analyzing and breaking down requirements into implementable steps."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the RequirementAnalysisAgent.
        
        Args:
            llm: The language model to use for analysis
        """
        self.llm = llm
        self.output_parser = CommaSeparatedListOutputParser()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a requirements analysis expert. Break down requirements into specific, 
            implementable code tasks. Focus on:
            - Concrete components to build (e.g., "Create a User class with authentication methods")
            - Specific files to create (e.g., "Implement user authentication in output/src/auth/user.js")
            - Technical implementation details (e.g., "Add JWT token validation middleware")
            - Dependencies between components
            
            Each task should be specific enough to generate code for. Break down large features into
            smaller, implementable pieces. Format tasks as a comma-separated list.
            
            Example tasks:
            - Create User model with email/password fields in output/src/models/user.js
            - Implement JWT authentication middleware in output/src/middleware/auth.js
            - Add login form component with validation in output/src/components/LoginForm.js"""),
            ("human", """Break down the following requirements into specific code tasks:
            {requirements}
            
            Focus on actual code components and files to create, not project management steps.""")
        ])
    
    async def analyze(self, requirements: str) -> List[str]:
        """Analyze requirements and break them down into implementable steps.
        
        Args:
            requirements: The original requirements to analyze
            
        Returns:
            A list of clear, implementable steps
        """
        chain = self.prompt | self.llm | self.output_parser
        try:
            result = await chain.ainvoke({"requirements": requirements})
            # Clean and validate the requirements
            cleaned_requirements = [req.strip() for req in result if req.strip()]
            return cleaned_requirements
        except Exception as e:
            raise ValueError(f"Failed to analyze requirements: {str(e)}")
    
    def _validate_requirements(self, requirements: List[str]) -> List[str]:
        """Validate and clean the analyzed requirements.
        
        Args:
            requirements: List of requirements to validate
            
        Returns:
            Validated and cleaned requirements
            
        Raises:
            ValueError: If requirements are invalid
        """
        if not requirements:
            raise ValueError("No valid requirements generated")
        
        # Remove duplicates while preserving order
        seen = set()
        validated = []
        for req in requirements:
            if req not in seen:
                seen.add(req)
                validated.append(req)
        
        return validated
