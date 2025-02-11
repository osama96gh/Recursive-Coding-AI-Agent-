"""Main entry point for the recursive development agent."""
import asyncio
import os
import json
import logging
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

from src.agents.base import RecursiveAgent
from src.config import validate_config
from src.state.schema import ProjectState, CodeGenerationStatus

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
    
    # Create file handler for detailed logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / f"agent_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    root_logger.addHandler(file_handler)
    
    # Configure specific loggers
    workflow_logger = logging.getLogger('workflow')
    workflow_logger.setLevel(logging.INFO)
    
    # Disable noisy logs
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    
    # Get module logger and log initialization
    module_logger = logging.getLogger(__name__)
    module_logger.info("Logging initialized")
    module_logger.info(f"Detailed logs will be written to: {log_file}")
    
    return module_logger

# Set up logging and get logger
logger = setup_logging()

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
        logger.info("="*80)
        logger.info("Starting AI-Controlled Development Agent")
        logger.info("="*80)
        
        # Initialize the application
        app = RecursiveAgentApp()
        logger.info("Agent application initialized successfully")
        
        print("\nAI-Controlled Development Agent initialized successfully.")
        print("Enter 'quit' to exit.")
        
        while True:
            # Get user input
            request = input("\nEnter your request: ").strip()
            
            if request.lower() == 'quit':
                logger.info("Received quit command")
                break
            
            if not request:
                logger.info("Received empty request, continuing...")
                continue
            
            logger.info("-"*80)
            logger.info(f"Processing request: {request}")
            
            while True:
                # Process the request with detailed logging
                logger.info(f"\nProcessing request: {request}")
                result = await app.process_request(request)
                
                # Display result based on status
                if result.get("status") == "needs_input":
                    logger.info(f"AI needs human input: {result.get('query')}")
                    print(f"\nAI needs your input: {result.get('query')}")
                    user_input = input("Your response: ").strip()
                    if user_input:
                        logger.info(f"Received user input: {user_input}")
                        request = user_input
                        continue
                
                elif result.get("status") == "success":
                    state = result.get("state", {})
                    logger.info("Processing successful result")
                    
                    # Handle error state
                    if state.get("status") == CodeGenerationStatus.ERROR:
                        error_msg = state.get('error_log', ['Unknown error'])[-1]
                        logger.error(f"Error state: {error_msg}")
                        print(f"\nError: {error_msg}")
                        break
                    
                    # Show current action and status
                    if state.get("current_action"):
                        action_info = f"\nCurrent Action: {state['current_action']}"
                        logger.info(action_info)
                        print(action_info)
                    
                    status_info = f"Status: {state.get('status', 'unknown')}"
                    step_info = f"Step Count: {state.get('step_count', 0)}"
                    logger.info(status_info)
                    logger.info(step_info)
                    print(status_info)
                    print(step_info)
                
                    # Show components
                    if state.get("components"):
                        logger.info(f"Components: {len(state['components'])}")
                        print("\nCode Components:")
                        for path, component in state["components"].items():
                            component_info = f"- {path} ({component.get('status', 'unknown')})"
                            logger.info(component_info)
                            print(component_info)
                
                    # Show test results
                    if state.get("test_results"):
                        logger.info(f"Test Results: {len(state['test_results'])}")
                        print("\nTest Results:")
                        for path, results in state["test_results"].items():
                            latest = results[-1] if results else None
                            if latest:
                                status = "✅" if latest.get("passed") else "❌"
                                result_info = f"- {path}: {status}"
                                logger.info(result_info)
                                print(result_info)
                                
                                if not latest.get("passed"):
                                    error_msg = f"  Error: {latest.get('error_message', 'Unknown error')}"
                                    logger.error(error_msg)
                                    print(error_msg)
                                
                                if latest.get("suggestions"):
                                    logger.info(f"  Suggestions: {len(latest['suggestions'])}")
                                    print("  Suggestions:")
                                    for suggestion in latest["suggestions"]:
                                        logger.info(f"  * {suggestion}")
                                        print(f"  * {suggestion}")
                
                    # Show recent actions
                    if state.get("action_history"):
                        recent_actions = state["action_history"][-3:]  # Last 3 actions
                        logger.info(f"Recent Actions: {len(recent_actions)}")
                        print("\nRecent Actions:")
                        for action in recent_actions:
                            logger.info(f"- {action}")
                            print(f"- {action}")
                    
                    # Show development history
                    if state.get("development_history"):
                        latest_entry = state["development_history"][-1]
                        history_info = [
                            "\nDevelopment History:",
                            f"Step {latest_entry['step']} completed at {latest_entry['timestamp']}"
                        ]
                        if latest_entry.get("action"):
                            history_info.append(f"Action: {latest_entry['action']}")
                        
                        for line in history_info:
                            logger.info(line)
                            print(line)
                
                    break
                else:
                    error_msg = result.get("error", "Unknown error occurred")
                    logger.error(f"Error processing request: {error_msg}")
                    print("\nError:", error_msg)
                    logger.info("Breaking due to error")
                    break
    
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"Error: {str(e)}")
        return 1
    
    logger.info("="*80)
    logger.info("AI-Controlled Development Agent shutting down")
    logger.info("="*80)
    print("\nGoodbye!")
    return 0

if __name__ == "__main__":
    asyncio.run(main())
