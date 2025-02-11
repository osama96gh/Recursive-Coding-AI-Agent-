from typing import Dict, Any, Optional

class StructuredPromptGenerator:
    """Generates structured prompts with explicit output format instructions."""

    def _get_base_format_instructions(self) -> str:
        """Get base format instructions for all prompts."""
        return """
You must respond with ONLY a JSON object, no additional text or explanation.
Your response must include these base fields:
{
    "step_id": "auto-generated",
    "timestamp": "auto-generated",
    "status": "string (completed, error, etc.)",
    "confidence_score": "float between 0 and 1",
    "metadata": {
        "additional_info": "any relevant metadata"
    }
}"""

    def _get_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for code analysis."""
        return f"""Analyze the following code context and provide structured insights:
{context}

{self._get_base_format_instructions()}

Your JSON response must also include:
{{
    "insights": ["list of key insights about the code"],
    "recommendations": ["list of specific recommendations"],
    "code_quality_metrics": {{
        "complexity": "float score",
        "maintainability": "float score",
        "documentation": "float score"
    }},
    "priority_actions": ["ordered list of actions to take"]
}}"""

    def _get_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for code generation."""
        return f"""Generate code based on the following requirements and context:
{context}

{self._get_base_format_instructions()}

Your JSON response must also include:
{{
    "file_path": "string (path where code should be saved)",
    "content": "string (the actual code)",
    "language": "string (programming language)",
    "dependencies": ["list of required dependencies"],
    "quality_checks": {{
        "syntax_valid": "boolean",
        "follows_style_guide": "boolean",
        "has_documentation": "boolean"
    }},
    "generation_context": {{
        "requirements_addressed": ["list of requirements this code addresses"],
        "assumptions_made": ["list of assumptions"]
    }},
    "validation_results": [
        {{
            "check_name": "string",
            "passed": "boolean",
            "message": "string"
        }}
    ]
}}"""

    def _get_testing_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for test execution."""
        return f"""Execute tests on the following code:
{context}

{self._get_base_format_instructions()}

Your JSON response must also include:
{{
    "test_cases": [
        {{
            "name": "string",
            "description": "string",
            "status": "string (passed/failed)",
            "execution_time": "float (seconds)"
        }}
    ],
    "coverage": {{
        "line_coverage": "float percentage",
        "branch_coverage": "float percentage",
        "function_coverage": "float percentage"
    }},
    "performance_metrics": {{
        "execution_time": "float (seconds)",
        "memory_usage": "float (MB)"
    }},
    "failures": [
        {{
            "test_name": "string",
            "message": "string",
            "stack_trace": "string"
        }}
    ]
}}"""

    def _get_error_handling_prompt(self, context: Dict[str, Any]) -> str:
        """Generate prompt for error handling scenarios."""
        return f"""Handle the following error scenario:
{context}

{self._get_base_format_instructions()}

Your JSON response must also include:
{{
    "error_analysis": {{
        "error_type": "string",
        "severity": "string (low/medium/high)",
        "impact": "string"
    }},
    "recovery_steps": ["ordered list of steps to recover"],
    "prevention_suggestions": ["list of ways to prevent this error"]
}}"""

    def generate_prompt(
        self, 
        action_type: str, 
        context: Dict[str, Any],
        additional_instructions: Optional[str] = None
    ) -> str:
        """Generate a structured prompt based on action type and context."""
        prompt_generators = {
            "analyze": self._get_analysis_prompt,
            "generate": self._get_generation_prompt,
            "test": self._get_testing_prompt,
            "handle_error": self._get_error_handling_prompt
        }

        if action_type not in prompt_generators:
            raise ValueError(f"Unknown action type: {action_type}")

        prompt = prompt_generators[action_type](context)
        
        if additional_instructions:
            prompt += f"\n\nAdditional Instructions:\n{additional_instructions}"

        return prompt

    def get_repair_prompt(self, malformed_output: str, expected_schema: Dict[str, Any]) -> str:
        """Generate a prompt to repair malformed output."""
        return f"""The following output was malformed:
{malformed_output}

{self._get_base_format_instructions()}

The output should follow this schema:
{expected_schema}

Fix the output to match the required schema exactly. Respond with ONLY the corrected JSON object."""
