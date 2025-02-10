"""Configuration management for the recursive agent project."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
MEMLOG_DIR = PROJECT_ROOT / "memlog"
SRC_DIR = PROJECT_ROOT / "src"

# OpenAI configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4-turbo-preview")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4000"))

# Git configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Agent configuration
DEFAULT_AGENT_CONFIG = {
    "model": MODEL_NAME,
    "temperature": TEMPERATURE,
    "max_tokens": MAX_TOKENS,
}

# Project state tracking
STATE_FILE = MEMLOG_DIR / "project_state.json"
HISTORY_FILE = MEMLOG_DIR / "development_history.json"

def validate_config():
    """Validate the configuration and ensure required directories exist."""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY must be set in .env file")
    
    # Ensure required directories exist
    MEMLOG_DIR.mkdir(parents=True, exist_ok=True)
    
    return True

def get_agent_config(overrides=None):
    """Get agent configuration with optional overrides."""
    config = DEFAULT_AGENT_CONFIG.copy()
    if overrides:
        config.update(overrides)
    return config
