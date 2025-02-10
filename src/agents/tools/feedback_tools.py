"""Tools for getting human feedback."""
from typing import Dict, List
from langchain.tools import Tool, StructuredTool

from .schemas import HumanFeedbackInput

class FeedbackTools:
    """Collection of tools for getting human feedback."""
    
    def __init__(self):
        """Initialize feedback tools."""
        pass
    
    def ask_human(self, input: HumanFeedbackInput) -> Dict:
        """Ask the human for feedback or clarification."""
        try:
            # Print a newline for better readability
            print("\n[Agent needs clarification]")
            print(f"Question: {input.question}")
            
            # Get user input
            response = input("Your response: ").strip()
            
            return {
                "status": "success",
                "response": response
            }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def get_tools(self) -> List[Tool]:
        """Get all feedback tools."""
        return [
            Tool(
                name="ask_human",
                description="Ask the human for feedback or clarification about something",
                func=self.ask_human,
                args_schema=HumanFeedbackInput
            )
        ]
