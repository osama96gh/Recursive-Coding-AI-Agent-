from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any

class CodeGenerationStatus(str, Enum):
    INITIAL = "initial"
    IN_PROGRESS = "in_progress"
    NEEDS_HUMAN_INPUT = "needs_human_input"
    COMPLETE = "complete"
    ERROR = "error"

class ActionDecision(BaseModel):
    action_type: str
    description: str
    needs_human_input: bool = False
    human_query: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    
    def __str__(self):
        return f"{self.action_type}: {self.description}"

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
    suggestions: List[str] = Field(default_factory=list)

class ProjectState(BaseModel):
    # Core tracking
    status: CodeGenerationStatus = Field(default=CodeGenerationStatus.INITIAL)
    
    # Requirements and context
    original_requirements: str
    current_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Code management
    components: Dict[str, CodeComponent] = Field(default_factory=dict)
    test_results: Dict[str, List[TestResult]] = Field(default_factory=dict)
    
    # AI decision tracking
    current_action: Optional[ActionDecision] = None
    action_history: List[ActionDecision] = Field(default_factory=list)
    
    # Human interaction
    needs_human_input: bool = False
    human_query: Optional[str] = None
    human_feedback: Optional[str] = None
    
    # Progress tracking
    step_count: int = Field(default=0)
    max_steps: int = Field(default=50)  # Safety limit
    
    # Memory and history
    error_log: List[str] = Field(default_factory=list)
    development_history: List[Dict] = Field(default_factory=list)
