"""Base agent implementation for recursive project development."""
from typing import Dict, List, Optional, Any
import json
import datetime
import logging
from pathlib import Path

from langchain_openai import ChatOpenAI

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

from ..config import get_agent_config, STATE_FILE, HISTORY_FILE, PROJECT_ROOT
from ..state.schema import ProjectState, CodeGenerationStatus
from ..workflows.ai_workflow import AIControlledWorkflow

class RecursiveAgent:
    """Agent that recursively develops and enhances software projects."""
    
    def __init__(self, config_overrides: Optional[Dict] = None):
        """Initialize the recursive agent with optional configuration overrides."""
        self.config = get_agent_config(config_overrides)
        self.llm = ChatOpenAI(**self.config)
        
        # Initialize AI-controlled workflow
        try:
            self.workflow = AIControlledWorkflow(self.llm)
            logger.info("AI-controlled workflow initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize workflow: {e}")
            raise
        
        # Initialize state and history
        self.state = self._load_state()
        self.history = self._load_history()
    
    def _load_state(self) -> ProjectState:
        """Load the current project state."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                # Create new state with loaded data
                return ProjectState(
                    status=CodeGenerationStatus(data.get("status", "initial")),
                    original_requirements=data.get("original_requirements", ""),
                    **{k: v for k, v in data.items() if k not in ["status", "original_requirements"]}
                )
            else:
                # Initialize new state
                return ProjectState(
                    status=CodeGenerationStatus.INITIAL,
                    original_requirements=""
                )
        except Exception as e:
            logger.error(f"Error loading state, initializing new: {e}")
            return ProjectState(
                status=CodeGenerationStatus.INITIAL,
                original_requirements=""
            )
    
    def _load_history(self) -> List[Dict]:
        """Load the development history."""
        if HISTORY_FILE.exists():
            return json.loads(HISTORY_FILE.read_text())
        return []
    
    def _save_state(self):
        """Save the current project state."""
        STATE_FILE.write_text(json.dumps(self.state.model_dump(), indent=2))
    
    def _save_history(self):
        """Save the development history."""
        HISTORY_FILE.write_text(json.dumps(self.history, indent=2))
    
    def _add_to_history(self, action: str, details: Dict):
        """Add an action to the development history."""
        entry = {
            "action": action,
            "details": details,
            "timestamp": str(datetime.datetime.now())
        }
        self.history.append(entry)
        self._save_history()
    
    async def process_request(self, request: str) -> Dict:
        """Process a user request and return the result."""
        try:
            logger.info("="*80)
            logger.info(f"Processing new request: {request}")
            logger.info("="*80)
            
            # Log initial state
            logger.info("Current state before processing:")
            logger.info(f"- Status: {self.state.status}")
            logger.info(f"- Step count: {self.state.step_count}")
            logger.info(f"- Components: {len(self.state.components)}")
            logger.info(f"- Test results: {len(self.state.test_results)}")
            
            # Update state with new request
            self.state.original_requirements = request
            logger.info("Updated state with new requirements")
            
            # Execute the workflow
            logger.info("\nStarting workflow execution...")
            try:
                # The workflow returns the final state
                final_state = await self.workflow.workflow.ainvoke(self.state.model_dump())
                logger.info("Workflow execution completed successfully")
                
                # Convert final state back to ProjectState
                self.state = ProjectState(**final_state)
                logger.info("\nWorkflow execution completed")
                logger.info("Final state summary:")
                logger.info(f"- Status: {self.state.status}")
                logger.info(f"- Step count: {self.state.step_count}")
                logger.info(f"- Components: {len(self.state.components)}")
                logger.info(f"- Test results: {len(self.state.test_results)}")
                
                # Check if we need human input
                if self.state.status == CodeGenerationStatus.NEEDS_HUMAN_INPUT:
                    logger.info(f"\nWorkflow needs human input:")
                    logger.info(f"Query: {self.state.human_query}")
                    return {
                        "status": "needs_input",
                        "query": self.state.human_query,
                        "state": self.state.model_dump()
                    }
                
                # Log any error messages
                if self.state.error_log:
                    logger.info("\nError log entries:")
                    for error in self.state.error_log:
                        logger.error(f"- {error}")
                
                # Save state and history
                logger.info("\nSaving state and history...")
                self._save_state()
                self._add_to_history("process_request", {
                    "request": request,
                    "final_state": self.state.model_dump()
                })
                logger.info("State and history saved successfully")
                
                return {
                    "status": "success",
                    "state": self.state.model_dump()
                }
                
            except Exception as graph_error:
                logger.error("\nWorkflow execution failed:")
                logger.error(f"Error type: {type(graph_error).__name__}")
                logger.error(f"Error message: {str(graph_error)}")
                logger.error("Stack trace:", exc_info=True)
                raise graph_error
            
        except Exception as e:
            logger.error("\nRequest processing failed:")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error message: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            error_details = {
                "error": str(e),
                "request": request,
                "state": self.state.model_dump()
            }
            self._add_to_history("error", error_details)
            return {
                "status": "error",
                "error": str(e),
                "state": self.state.model_dump()
            }
    
    def get_current_state(self) -> ProjectState:
        """Get the current project state."""
        return self.state
    
    def get_development_history(self) -> List[Dict]:
        """Get the development history."""
        return self.history
