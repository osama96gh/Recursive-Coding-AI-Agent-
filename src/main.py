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
                state_str += f"\n- Phase: {state_info.get('current_phase', 'unknown')}"
                state_str += f"\n- Status: {state_info.get('status', 'unknown')}"
                state_str += f"\n- Cycle: {state_info.get('cycle_count', 0)}"
                state_str += f"\n- Iteration: {state_info.get('iteration_count', 0)}"
                
                # Add requirements if present
                if state_info.get('current_requirements'):
                    state_str += "\n- Current Requirements:"
                    for req in state_info['current_requirements']:
                        state_str += f"\n  * {req}"
                
                # Add components if present
                if state_info.get('components'):
                    state_str += "\n- Components:"
                    for path, comp in state_info['components'].items():
                        state_str += f"\n  * {path} ({comp.get('status', 'unknown')})"
                
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
                # Process the request with detailed logging
                logger.info(f"\nProcessing new request: {request}")
                logger.info("Starting recursive development workflow")
                result = await app.process_request(request)
                
                if result.get("status") == "success":
                    logger.info("Request processed successfully", extra={"state": result.get("state", {})})
                
                # Display result
                if result.get("status") == "success":
                    state = result.get("state", {})
                    
                    # Handle error state
                    if state.get("status") == CodeGenerationStatus.ERROR:
                        print(f"\nError: {state.get('error_log', ['Unknown error'])[-1]}")
                        break
                    
                    # Show project state and cycle info
                    print(f"\nCurrent project state: {state.get('current_phase', 'unknown')}")
                    print(f"Status: {state.get('status', 'unknown')}")
                    print(f"Development cycle: {state.get('cycle_count', 0)}")
                    print(f"Current iteration: {state.get('iteration_count', 0)}")
                    
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
                    
                    # Show development history
                    if state.get("development_history"):
                        print("\nDevelopment History:")
                        latest_cycle = state["development_history"][-1]
                        print(f"Cycle {latest_cycle['cycle']} completed at {latest_cycle['timestamp']}")
                        if latest_cycle.get("components"):
                            print("Components developed:")
                            for path in latest_cycle["components"].keys():
                                print(f"- {path}")
                    
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
