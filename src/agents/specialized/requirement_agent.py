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
            ("system", """You are a requirements analysis expert. Break down requirements into clear, 
            implementable steps. Focus on:
            - Technical feasibility
            - Dependencies between steps
            - Clear success criteria
            - Implementation complexity
            
            Format your response as a comma-separated list of steps."""),
            ("human", "{requirements}")
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
