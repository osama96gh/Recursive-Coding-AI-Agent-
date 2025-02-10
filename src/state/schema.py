from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class CodeGenerationStatus(Enum):
    INITIAL = "initial"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    TESTING = "testing"
    REFINING = "refining"
    COMPLETE = "complete"
    ERROR = "error"

class CodeComponent(BaseModel):
    file_path: str
    content: str
    language: str
    dependencies: List[str] = Field(default_factory=list)
    status: str = "pending"
    version: int = 1

class TestResult(BaseModel):
    component_path: str
    status: str
    passed: bool
    error_message: Optional[str] = None
    execution_time: float

class ProjectState(BaseModel):
    # Core tracking
    status: CodeGenerationStatus = Field(default=CodeGenerationStatus.INITIAL)
    current_phase: str = Field(default="planning")
    
    # Requirements
    original_requirements: str
    current_requirements: List[str] = Field(default_factory=list)
    
    # Code management
    components: Dict[str, CodeComponent] = Field(default_factory=dict)
    test_results: Dict[str, List[TestResult]] = Field(default_factory=dict)
    
    # Progress tracking
    iteration_count: int = Field(default=0)
    max_iterations: int = Field(default=5)
    features: List[Dict] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)
    
    # Memory
    messages: List[Dict] = Field(default_factory=list)
    error_log: List[str] = Field(default_factory=list)
    tools_output: Dict = Field(default_factory=dict)
