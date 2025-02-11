from typing import Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

from src.state.schema import CodeComponent, CodeGenerationOutput, EnhancedActionResult
from src.agents.tools.output_validator import OutputValidator
from src.agents.tools.prompt_generator import StructuredPromptGenerator

class CodeGenerationAgent:
    """Agent responsible for generating high-quality code based on requirements."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize the CodeGenerationAgent.
        
        Args:
            llm: The language model to use for code generation
        """
        self.llm = llm
        self.output_validator = OutputValidator()
        self.prompt_generator = StructuredPromptGenerator()
    
    async def generate(self, requirement: str, context: Optional[Dict] = None) -> EnhancedActionResult:
        """Generate code based on the given requirement.
        
        Args:
            requirement: The requirement to implement
            context: Optional context about the project/codebase
            
        Returns:
            A CodeComponent containing the generated code
        """
        try:
            # Generate structured prompt
            generation_context = {
                "requirement": requirement,
                "base_path": "output/",
                **context if context else {}
            }
            
            prompt = self.prompt_generator.generate_prompt(
                "generate",
                generation_context,
                additional_instructions="""All generated code should be placed in the 'output' directory.
Consider:
- Best practices and patterns
- Error handling and edge cases
- Code documentation
- Testing considerations

Example file paths:
- output/main.py
- output/src/components/app.js
- output/lib/utils.ts"""
            )
            
            # Execute through LLM
            messages = [
                SystemMessage(content="You are an expert code generator."),
                HumanMessage(content=prompt)
            ]
            response = await self.llm.ainvoke(messages)
            
            # Validate and parse output
            content = response.content if hasattr(response, 'content') else str(response)
            validated_result = await self.output_validator.validate_and_parse(
                content,
                "generate",
                context=generation_context
            )
            
            # Ensure file path is within output directory
            output = validated_result.output
            if isinstance(output, CodeGenerationOutput):
                if not output.file_path.startswith("output/"):
                    output.file_path = f"output/{output.file_path.lstrip('/')}"
            
            return validated_result
            
        except Exception as e:
            # Try to repair malformed output if possible
            try:
                repaired_output = await self.output_validator.repair_malformed_output(
                    content if 'content' in locals() else str(e),
                    "generate",
                    self._get_generation_schema()
                )
                validated_result = await self.output_validator.validate_and_parse(
                    repaired_output,
                    "generate",
                    context=generation_context
                )
                return validated_result
            except Exception as repair_error:
                raise ValueError(f"Failed to generate code: {str(e)}. Repair attempt failed: {str(repair_error)}")
    
    def _get_generation_schema(self) -> Dict[str, Any]:
        """Get the expected schema for code generation output."""
        return {
            "file_path": "string",
            "content": "string",
            "language": "string",
            "dependencies": ["string"],
            "quality_checks": {
                "syntax_valid": "boolean",
                "follows_style_guide": "boolean",
                "has_documentation": "boolean"
            },
            "generation_context": {
                "requirements_addressed": ["string"],
                "assumptions_made": ["string"]
            },
            "validation_results": [
                {
                    "check_name": "string",
                    "passed": "boolean",
                    "message": "string"
                }
            ]
        }
