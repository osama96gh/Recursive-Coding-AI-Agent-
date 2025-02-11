from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union

class CodeGenerationStatus(str, Enum):
    INITIAL = "initial"
    IN_PROGRESS = "in_progress"
    NEEDS_HUMAN_INPUT = "needs_human_input"
    COMPLETE = "complete"
    ERROR = "error"

class AIStepOutput(BaseModel):
    """Base model for all AI step outputs"""
    step_id: str = Field(..., description="Unique identifier for this step")
    status: str = Field(..., description="Status of this step")
    confidence_score: float = Field(..., ge=0, le=1, description="Confidence score for this output")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata about the step")

class CodeAnalysisOutput(AIStepOutput):
    """Structured output for code analysis steps"""
    insights: List[str] = Field(..., description="Key insights from the analysis")
    recommendations: List[str] = Field(..., description="Recommended actions")
    code_quality_metrics: Dict[str, float] = Field(
        ..., 
        description="Metrics like complexity, maintainability"
    )
    priority_actions: List[str] = Field(..., description="Actions that should be taken first")

class CodeGenerationOutput(AIStepOutput):
    """Structured output for code generation steps"""
    file_path: str = Field(..., description="Path where the file will be created")
    content: str = Field(..., description="The generated code")
    language: str = Field(..., description="Programming language used")
    dependencies: List[str] = Field(default_factory=list, description="Required dependencies")
    quality_checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Results of various quality checks"
    )
    generation_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context used for generation"
    )
    validation_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Results of validation checks"
    )

class TestExecutionOutput(AIStepOutput):
    """Structured output for test execution steps"""
    test_cases: List[Dict[str, Any]] = Field(..., description="Details of executed tests")
    coverage: Dict[str, float] = Field(..., description="Code coverage metrics")
    performance_metrics: Optional[Dict[str, float]] = Field(
        None,
        description="Optional performance measurements"
    )
    failures: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Details of any test failures"
    )

class EnhancedActionResult(BaseModel):
    """Enhanced structure for action results"""
    action_type: str = Field(..., description="Type of action performed")
    output: Union[CodeAnalysisOutput, CodeGenerationOutput, TestExecutionOutput] = Field(
        ..., 
        description="Structured output from the action"
    )
    execution_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the execution"
    )
    error_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Context about any errors that occurred"
    )

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

    def model_dump(self, **kwargs):
        """Override model_dump to ensure proper serialization"""
        return {
            "file_path": self.file_path,
            "content": self.content,
            "language": self.language,
            "dependencies": self.dependencies,
            "status": self.status,
            "version": self.version
        }

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
