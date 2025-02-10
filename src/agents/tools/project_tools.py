"""Tools for project analysis and management."""
from typing import Dict, List, Optional
import json
from pathlib import Path
import ast
import re

from langchain.tools import Tool, StructuredTool
from .schemas import ProjectAnalysisInput, ImprovementSuggestionInput
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import JsonOutputParser

class ProjectTools:
    """Collection of tools for project analysis and management."""
    
    def __init__(self, llm: ChatOpenAI, project_root: Path):
        """Initialize project tools with language model and project root."""
        self.llm = llm
        self.project_root = project_root
        self.parser = JsonOutputParser()
    
    def analyze_project_structure(self, input: ProjectAnalysisInput) -> Dict:
        """Analyze the structure of a project directory."""
        try:
            dir_path = (self.project_root / input.path).resolve()
            if not str(dir_path).startswith(str(self.project_root)):
                raise ValueError(f"Path {input.path} is outside project root")
            
            structure = {
                "files": [],
                "directories": [],
                "languages": set(),
                "dependencies": set()
            }
            
            def analyze_directory(current_path: Path, rel_path: Path = Path(".")):
                for item in current_path.iterdir():
                    if item.is_file():
                        rel_file = rel_path / item.name
                        structure["files"].append(str(rel_file))
                        
                        # Detect language and dependencies
                        if item.suffix in ['.py', '.js', '.ts', '.java']:
                            structure["languages"].add(item.suffix[1:])
                            if item.suffix == '.py':
                                self._analyze_python_imports(item, structure["dependencies"])
                            elif item.suffix in ['.js', '.ts']:
                                self._analyze_js_imports(item, structure["dependencies"])
                    
                    elif item.is_dir() and item.name not in ['.git', 'node_modules', 'venv', '__pycache__']:
                        rel_dir = rel_path / item.name
                        structure["directories"].append(str(rel_dir))
                        analyze_directory(item, rel_dir)
            
            analyze_directory(dir_path)
            
            # Convert sets to lists for JSON serialization
            structure["languages"] = list(structure["languages"])
            structure["dependencies"] = list(structure["dependencies"])
            
            return {
                "status": "success",
                "structure": structure
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _analyze_python_imports(self, file_path: Path, dependencies: set):
        """Analyze Python file imports."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for name in node.names:
                        dependencies.add(name.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.add(node.module.split('.')[0])
        except:
            pass
    
    def _analyze_js_imports(self, file_path: Path, dependencies: set):
        """Analyze JavaScript/TypeScript file imports."""
        try:
            content = file_path.read_text()
            # Match import statements
            import_patterns = [
                r'import.*?from [\'"](@?[^\'".]+)[\'"]',  # ES6 imports
                r'require\([\'"](@?[^\'".]+)[\'"]\)',     # CommonJS requires
            ]
            
            for pattern in import_patterns:
                for match in re.finditer(pattern, content):
                    package = match.group(1)
                    if not package.startswith('.'):
                        dependencies.add(package)
        except:
            pass
    
    def suggest_improvements(self, input: ImprovementSuggestionInput) -> Dict:
        """Suggest project improvements based on analysis."""
        prompt = PromptTemplate.from_template(
            """You are an expert project architect. Analyze the project structure and suggest improvements.
Consider:
- Code organization and modularity
- Missing essential files (README, tests, etc.)
- Development workflow improvements
- Best practices for the detected languages
Return suggestions in a JSON structure with clear, actionable items.

Project structure to analyze: {analysis}"""
        )
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({"analysis": json.dumps(input.analysis)})
            return {
                "status": "success",
                "suggestions": result
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_tools(self) -> List[Tool]:
        """Get all project analysis tools."""
        return [
            Tool(
                name="analyze_project_structure",
                description="Analyze the structure of a project directory",
                func=self.analyze_project_structure,
                args_schema=ProjectAnalysisInput
            ),
            Tool(
                name="suggest_improvements",
                description="Suggest project improvements based on analysis",
                func=self.suggest_improvements,
                args_schema=ImprovementSuggestionInput
            )
        ]
