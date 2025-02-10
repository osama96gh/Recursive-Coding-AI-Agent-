"""Tools for code generation and manipulation."""
from typing import Dict, List, Optional
import json
from pathlib import Path

from langchain.tools import Tool, StructuredTool
from .schemas import CodeGenerationSpec, CodeAnalysisInput
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import JsonOutputParser

class CodeTools:
    """Collection of tools for code generation and analysis."""
    
    def __init__(self, llm: ChatOpenAI):
        """Initialize code tools with a language model."""
        self.llm = llm
        self.parser = JsonOutputParser()
    
    def generate_code(self, input: CodeGenerationSpec) -> Dict:
        """Generate code based on a specification."""
        prompt = PromptTemplate.from_template(
            """You are an expert code generator. Generate code based on the provided specification.
Follow these guidelines:
- Use modern best practices and patterns
- Include necessary imports
- Add comprehensive docstrings and comments
- Consider error handling and edge cases
- Return the code and suggested file path in a JSON structure

Type: {type}
Requirements:
{requirements}
Context: {context}"""
        )
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "type": input.type,
                "requirements": "\n".join(f"- {req}" for req in input.requirements),
                "context": json.dumps(input.context) if input.context else "{}"
            })
            return {
                "status": "success",
                "code": result.get("code"),
                "file_path": result.get("file_path"),
                "language": result.get("language", "python")
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def analyze_code(self, input: CodeAnalysisInput) -> Dict:
        """Analyze code and suggest improvements."""
        prompt = PromptTemplate.from_template(
            """You are an expert code analyzer. Analyze the provided code and suggest improvements.
Consider:
- Code structure and organization
- Performance optimizations
- Security considerations
- Best practices adherence
- Potential bugs or issues
Return analysis in a JSON structure.

Code to analyze: {code}
Additional context: {context}"""
        )
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "code": input.code,
                "context": json.dumps(input.context) if input.context else "{}"
            })
            return {
                "status": "success",
                "analysis": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_tools(self) -> List[Tool]:
        """Get all code-related tools."""
        return [
            Tool(
                name="generate_code",
                description="Generate code based on a specification",
                func=self.generate_code,
                args_schema=CodeGenerationSpec
            ),
            Tool(
                name="analyze_code",
                description="Analyze code and suggest improvements",
                func=self.analyze_code,
                args_schema=CodeAnalysisInput
            )
        ]
