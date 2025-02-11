from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.state.schema import CodeComponent

class CodeGenerationAgent:
    """Agent responsible for generating high-quality code based on requirements."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the CodeGenerationAgent.
        
        Args:
            llm: The language model to use for code generation
        """
        self.llm = llm
        self.output_parser = JsonOutputParser()
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert code generator. Generate high-quality, tested code based on requirements.
            Consider:
            - Best practices and patterns
            - Error handling and edge cases
            - Code documentation
            - Testing considerations
            
            All generated code should be placed in the 'output' directory.
            Format your response as a JSON object with:
            {
                "file_path": "output/path/to/file",
                "content": "generated code",
                "language": "programming language",
                "dependencies": ["list", "of", "dependencies"]
            }
            
            Example file paths:
            - output/main.py
            - output/src/components/app.js
            - output/lib/utils.ts"""),
            ("human", """Generate code for the following requirement:
            {requirement}
            
            Generate the code in the output directory. For example:
            - output/main.py for the main application
            - output/src/components/* for components
            - output/lib/* for utilities""")
        ])
    
    async def generate(self, requirement: str, context: Optional[Dict] = None) -> CodeComponent:
        """Generate code based on the given requirement.
        
        Args:
            requirement: The requirement to implement
            context: Optional context about the project/codebase
            
        Returns:
            A CodeComponent containing the generated code
        """
        chain = self.prompt | self.llm | self.output_parser
        try:
            # Prepare prompt arguments
            prompt_args = {
                "requirement": requirement
            }
            if context:
                prompt_args.update(context)
            
            result = await chain.ainvoke(prompt_args)
            
            # Create and return CodeComponent
            # Ensure file path is within output directory
            file_path = result["file_path"]
            if not file_path.startswith("output/"):
                file_path = f"output/{file_path.lstrip('/')}"
            
            return CodeComponent(
                file_path=file_path,
                content=result["content"],
                language=result["language"],
                dependencies=result["dependencies"],
                status="generated",
                version=1
            )
        except Exception as e:
            raise ValueError(f"Failed to generate code: {str(e)}")
    
    def _validate_code(self, code: str, language: str) -> bool:
        """Validate the generated code for basic syntax and structure.
        
        Args:
            code: The generated code to validate
            language: The programming language
            
        Returns:
            True if code is valid, False otherwise
        """
        # TODO: Implement language-specific validation
        if not code.strip():
            return False
        
        # Basic validation - ensure code isn't just comments
        code_lines = [line.strip() for line in code.split("\n") 
                     if line.strip() and not line.strip().startswith(("#", "//", "/*", "*", "*/"))]
        return len(code_lines) > 0
