"""Main entry point for the recursive development agent."""
import asyncio
import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

from src.agents.base import RecursiveAgent
from src.config import validate_config
from src.state.schema import ProjectState, CodeGenerationStatus

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RecursiveAgentApp:
    """Application wrapper for the recursive development agent."""
    
    def __init__(self, config_overrides: Optional[Dict] = None):
        """Initialize the application."""
        # Load environment variables
        load_dotenv()
        
        # Validate configuration
        validate_config()
        
        # Initialize agent
        self.agent = RecursiveAgent(config_overrides)
    
    async def process_request(self, request: str) -> Dict:
        """Process a user request through the agent."""
        return await self.agent.process_request(request)
    
    def get_current_state(self) -> ProjectState:
        """Get the current project state."""
        return self.agent.get_current_state()
    
    def get_development_history(self) -> List[Dict[str, Any]]:
        """Get the development history."""
        return self.agent.get_development_history()

async def main():
    """Main entry point."""
    try:
        # Initialize the application
        app = RecursiveAgentApp()
        
        print("Recursive Development Agent initialized successfully.")
        print("Enter 'quit' to exit.")
        
        while True:
            # Get user input
            request = input("\nEnter your request: ").strip()
            
            if request.lower() == 'quit':
                break
            
            if not request:
                continue
            
            while True:
                # Process the request
                print("\nProcessing request...")
                logger.debug(f"Processing request: {request}")
                result = await app.process_request(request)
                logger.debug(f"Got result: {result}")
                
                # Display result
                if result.get("status") == "success":
                    state = result.get("state", {})
                    
                    # Handle error state
                    if state.get("status") == CodeGenerationStatus.ERROR:
                        print(f"\nError: {state.get('error_log', ['Unknown error'])[-1]}")
                        break
                    
                    # Show project state
                    print(f"\nCurrent project state: {state.get('current_phase', 'unknown')}")
                    print(f"Status: {state.get('status', 'unknown')}")
                    
                    # Show requirements
                    if state.get("current_requirements"):
                        print("\nCurrent requirements:")
                        for req in state["current_requirements"]:
                            print(f"- {req}")
                    
                    # Show components
                    if state.get("components"):
                        print("\nCode components:")
                        for path, component in state["components"].items():
                            print(f"- {path} ({component.get('status', 'unknown')})")
                    
                    # Show test results
                    if state.get("test_results"):
                        print("\nTest results:")
                        for path, results in state["test_results"].items():
                            latest = results[-1] if results else None
                            if latest:
                                status = "✅" if latest.get("passed") else "❌"
                                print(f"- {path}: {status}")
                    
                    # Show next steps
                    if state.get("next_steps"):
                        print("\nNext steps:")
                        for step in state["next_steps"]:
                            print(f"- {step}")
                    
                    # Check if we need user input
                    if state.get("status") == CodeGenerationStatus.ANALYZING:
                        user_input = input("\nProvide additional context (or press Enter to continue): ").strip()
                        if user_input:
                            request = user_input
                            continue
                    
                    break
                else:
                    error_msg = result.get("error", "Unknown error occurred")
                    logger.error(f"Error processing request: {error_msg}")
                    print("\nError:", error_msg)
                    break
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    print("\nGoodbye!")
    return 0

if __name__ == "__main__":
    asyncio.run(main())
