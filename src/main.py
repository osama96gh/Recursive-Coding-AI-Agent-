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
class CustomFormatter(logging.Formatter):
    """Custom formatter that creates structured, readable logs with workflow details."""
    
    def format(self, record):
        if hasattr(record, 'state'):
            state_info = record.state
            if isinstance(state_info, dict):
                # Format detailed state information
                state_str = "\nState Details:"
                if state_info.get('current_action'):
                    state_str += f"\n- Current Action: {state_info['current_action']}"
                state_str += f"\n- Status: {state_info.get('status', 'unknown')}"
                state_str += f"\n- Step Count: {state_info.get('step_count', 0)}"
                
                # Add components if present
                if state_info.get('components'):
                    state_str += "\n- Components:"
                    for path, comp in state_info['components'].items():
                        state_str += f"\n  * {path} ({comp.get('status', 'unknown')})"
                
                # Add recent actions if present
                if state_info.get('action_history'):
                    state_str += "\n- Recent Actions:"
                    for action in state_info['action_history'][-3:]:  # Last 3 actions
                        state_str += f"\n  * {action}"
                
                return f"\n[{record.levelname}] {record.msg}{state_str}"
            return f"\n[{record.levelname}] {record.msg}\nState: {state_info}"
        return f"[{record.levelname}] {record.msg}"

def setup_logging():
    """Set up detailed logging configuration."""
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler with custom formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(CustomFormatter())
    root_logger.addHandler(console_handler)
    
    # Configure specific loggers
    workflow_logger = logging.getLogger('workflow')
    workflow_logger.setLevel(logging.INFO)
    
    # Disable noisy logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)

# Set up logging
setup_logging()
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
        
        print("AI-Controlled Development Agent initialized successfully.")
        print("Enter 'quit' to exit.")
        
        while True:
            # Get user input
            request = input("\nEnter your request: ").strip()
            
            if request.lower() == 'quit':
                break
            
            if not request:
                continue
            
            while True:
                # Process the request with detailed logging
                logger.info(f"\nProcessing request: {request}")
                result = await app.process_request(request)
                
                # Display result based on status
                if result.get("status") == "needs_input":
                    print(f"\nAI needs your input: {result.get('query')}")
                    user_input = input("Your response: ").strip()
                    if user_input:
                        request = user_input
                        continue
                    
                elif result.get("status") == "success":
                    state = result.get("state", {})
                    
                    # Handle error state
                    if state.get("status") == CodeGenerationStatus.ERROR:
                        print(f"\nError: {state.get('error_log', ['Unknown error'])[-1]}")
                        break
                    
                    # Show current action and status
                    if state.get("current_action"):
                        print(f"\nCurrent Action: {state['current_action']}")
                    print(f"Status: {state.get('status', 'unknown')}")
                    print(f"Step Count: {state.get('step_count', 0)}")
                    
                    # Show components
                    if state.get("components"):
                        print("\nCode Components:")
                        for path, component in state["components"].items():
                            print(f"- {path} ({component.get('status', 'unknown')})")
                    
                    # Show test results
                    if state.get("test_results"):
                        print("\nTest Results:")
                        for path, results in state["test_results"].items():
                            latest = results[-1] if results else None
                            if latest:
                                status = "✅" if latest.get("passed") else "❌"
                                print(f"- {path}: {status}")
                                if not latest.get("passed"):
                                    print(f"  Error: {latest.get('error_message', 'Unknown error')}")
                                if latest.get("suggestions"):
                                    print("  Suggestions:")
                                    for suggestion in latest["suggestions"]:
                                        print(f"  * {suggestion}")
                    
                    # Show recent actions
                    if state.get("action_history"):
                        print("\nRecent Actions:")
                        for action in state["action_history"][-3:]:  # Show last 3 actions
                            print(f"- {action}")
                    
                    # Show development history
                    if state.get("development_history"):
                        print("\nDevelopment History:")
                        latest_entry = state["development_history"][-1]
                        print(f"Step {latest_entry['step']} completed at {latest_entry['timestamp']}")
                        if latest_entry.get("action"):
                            print(f"Action: {latest_entry['action']}")
                    
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
