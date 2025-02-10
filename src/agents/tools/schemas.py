"""Schema definitions for tool inputs."""
from typing import List, Dict, Optional
from pydantic import BaseModel

class CodeGenerationSpec(BaseModel):
    """Schema for code generation specification."""
    type: str
    requirements: List[str]
    context: Optional[Dict] = None

class CodeAnalysisInput(BaseModel):
    """Schema for code analysis input."""
    code: str
    context: Optional[Dict] = None

class ProjectAnalysisInput(BaseModel):
    """Schema for project analysis input."""
    path: str = "."

class ImprovementSuggestionInput(BaseModel):
    """Schema for improvement suggestion input."""
    analysis: Dict

class HumanFeedbackInput(BaseModel):
    """Schema for requesting human feedback."""
    question: str
