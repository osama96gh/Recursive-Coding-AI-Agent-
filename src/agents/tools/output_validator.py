import json
import uuid
import logging
from typing import Type, Dict, Any, Optional, Union
from pydantic import ValidationError

from src.state.schema import (
    AIStepOutput,
    CodeAnalysisOutput,
    CodeGenerationOutput,
    TestExecutionOutput,
    EnhancedActionResult
)

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Remove existing handlers
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Create console handler with custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
logger.addHandler(console_handler)

class OutputValidator:
    """Validates and processes AI outputs to ensure consistent structure."""

    @staticmethod
    def _generate_step_id() -> str:
        """Generate a unique step ID."""
        return str(uuid.uuid4())

    @staticmethod
    def _extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from potentially noisy text output."""
        try:
            # First try direct JSON parsing
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON-like structure in the text
            try:
                start_idx = text.find("{")
                end_idx = text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    json_str = text[start_idx:end_idx + 1]
                    return json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                return None

    def _add_base_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Add base AIStepOutput fields if missing."""
        # Always set these fields with proper types
        data["step_id"] = self._generate_step_id()
        data["status"] = data.get("status", "completed")
        data["confidence_score"] = data.get("confidence_score", 0.8 if "error" not in data else 0.5)
        data["metadata"] = data.get("metadata", {})
        
        # Handle priority actions if present
        if "priority_actions" in data and isinstance(data["priority_actions"], list):
            # Convert any dict objects to strings
            data["priority_actions"] = [
                str(action) if isinstance(action, dict) else action
                for action in data["priority_actions"]
            ]
        
        # Handle insights if present
        if "insights" in data and isinstance(data["insights"], list):
            data["insights"] = [
                str(insight) if isinstance(insight, dict) else insight
                for insight in data["insights"]
            ]
        
        # Handle recommendations if present
        if "recommendations" in data and isinstance(data["recommendations"], list):
            data["recommendations"] = [
                str(rec) if isinstance(rec, dict) else rec
                for rec in data["recommendations"]
            ]
        
        return data

    async def validate_and_parse(
        self, 
        raw_output: str, 
        action_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> EnhancedActionResult:
        """Validate and parse raw LLM output into structured format."""
        try:
            logger.info(f"Starting validation for {action_type} output")
            logger.info(f"Raw output length: {len(raw_output)}")
            
            # Extract JSON from potentially noisy output
            data = self._extract_json_from_text(raw_output)
            if not data:
                logger.error("Failed to extract JSON from output")
                raise ValueError("Failed to extract JSON from output")
            logger.info(f"Successfully extracted JSON data with keys: {list(data.keys())}")

            # Add base fields
            logger.info("Adding base fields to data")
            data = self._add_base_fields(data)

            # Add context to metadata if provided
            if context:
                logger.info(f"Adding context to metadata: {context}")
                data["metadata"]["context"] = context

            # Create appropriate output type based on action
            logger.info(f"Creating output type for action: {action_type}")
            if action_type == "analyze":
                logger.info("Processing analysis output")
                # Ensure all list fields contain strings
                insights = [str(i) for i in data.get("insights", [])]
                recommendations = [str(r) for r in data.get("recommendations", [])]
                priority_actions = [str(p) for p in data.get("priority_actions", [])]
                
                output = CodeAnalysisOutput(
                    insights=insights,
                    recommendations=recommendations,
                    code_quality_metrics=data.get("code_quality_metrics", {
                        "complexity": 0.0,
                        "maintainability": 0.0,
                        "documentation": 0.0
                    }),
                    priority_actions=priority_actions,
                    **{k: v for k, v in data.items() if k in AIStepOutput.__fields__}
                )
            elif action_type == "generate":
                output = CodeGenerationOutput(
                    file_path=data.get("file_path", ""),
                    content=data.get("content", ""),
                    language=data.get("language", ""),
                    dependencies=data.get("dependencies", []),
                    quality_checks=data.get("quality_checks", {}),
                    generation_context=data.get("generation_context", {}),
                    validation_results=data.get("validation_results", []),
                    **{k: v for k, v in data.items() if k in AIStepOutput.__fields__}
                )
            elif action_type == "test":
                output = TestExecutionOutput(
                    test_cases=data.get("test_cases", []),
                    coverage=data.get("coverage", {}),
                    performance_metrics=data.get("performance_metrics"),
                    failures=data.get("failures", []),
                    **{k: v for k, v in data.items() if k in AIStepOutput.__fields__}
                )
            else:
                raise ValueError(f"Unknown action type: {action_type}")

            # Create enhanced action result
            logger.info("Creating enhanced action result")
            result = EnhancedActionResult(
                action_type=action_type,
                output=output,
                execution_metadata={
                    "raw_output_length": len(raw_output),
                    "validation_successful": True,
                    "validation_details": {
                        "output_type": output.__class__.__name__,
                        "fields_present": list(output.dict().keys())
                    }
                }
            )
            logger.info("Validation completed successfully")
            return result

        except (ValidationError, ValueError, KeyError) as e:
            logger.error(f"Validation error: {str(e)}")
            # Return error result with partial data if possible
            error_context = {
                "error_type": type(e).__name__,
                "error_message": str(e),
                "partial_data": data if "data" in locals() else None,
                "raw_output": raw_output[:500] + "..." if len(raw_output) > 500 else raw_output,
                "validation_stage": "data_extraction" if "data" not in locals() else "model_validation"
            }
            logger.error(f"Error context: {json.dumps(error_context, indent=2)}")
            
            # Try to create a basic output structure even in error case
            try:
                base_output = AIStepOutput(
                    step_id=self._generate_step_id(),
                    status="error",
                    confidence_score=0.0,
                    metadata={"error": str(e)}
                )
                
                return EnhancedActionResult(
                    action_type=action_type,
                    output=base_output,
                    execution_metadata={
                        "validation_successful": False
                    },
                    error_context=error_context
                )
            except Exception as inner_e:
                # If even basic output creation fails, raise the original error
                raise e

    async def repair_malformed_output(
        self, 
        raw_output: str, 
        action_type: str,
        expected_schema: Type[AIStepOutput]
    ) -> str:
        """Attempt to repair malformed LLM output."""
        try:
            logger.info(f"Attempting to repair malformed {action_type} output")
            # Extract any JSON-like structure
            data = self._extract_json_from_text(raw_output)
            logger.info("Extracted data from malformed output")
            if not data:
                # If no JSON found, try to create minimal valid structure
                data = {
                    "step_id": self._generate_step_id(),
                    "status": "repaired",
                    "confidence_score": 0.5,
                    "metadata": {"original_output": raw_output}
                }

            # Add required fields based on action type
            if action_type == "analyze":
                data.update({
                    "insights": data.get("insights", ["No insights available"]),
                    "recommendations": data.get("recommendations", ["No recommendations available"]),
                    "code_quality_metrics": data.get("code_quality_metrics", {"unknown": 0.0}),
                    "priority_actions": data.get("priority_actions", ["Review and fix output structure"])
                })
            elif action_type == "generate":
                data.update({
                    "file_path": data.get("file_path", "unknown_path"),
                    "content": data.get("content", "# Generated content unavailable"),
                    "language": data.get("language", "unknown"),
                    "dependencies": data.get("dependencies", [])
                })
            elif action_type == "test":
                data.update({
                    "test_cases": data.get("test_cases", [{"name": "unknown", "status": "error"}]),
                    "coverage": data.get("coverage", {"total": 0.0}),
                    "failures": data.get("failures", [{"message": "Output structure validation failed"}])
                })

            # Return repaired JSON string
            return json.dumps(data)

        except Exception as e:
            # If repair fails, return minimal valid JSON structure
            minimal_data = {
                "step_id": self._generate_step_id(),
                "status": "error",
                "confidence_score": 0.0,
                "metadata": {
                    "error": f"Output repair failed: {str(e)}",
                    "original_output": raw_output
                }
            }
            return json.dumps(minimal_data)
