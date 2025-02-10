"""Tests for the recursive development agent."""
import pytest
import asyncio
from pathlib import Path
import json

from src.agents.base import RecursiveAgent
from src.config import PROJECT_ROOT

@pytest.fixture
def test_config():
    """Test configuration fixture."""
    return {
        "model": "gpt-4-turbo-preview",
        "temperature": 0.5,
        "max_tokens": 2000
    }

@pytest.fixture
def agent(test_config):
    """RecursiveAgent fixture."""
    return RecursiveAgent(config_overrides=test_config)

@pytest.mark.asyncio
async def test_agent_initialization(agent):
    """Test agent initialization."""
    assert agent is not None
    assert agent.state is not None
    assert agent.state["status"] == "initialized"
    assert agent.state["current_phase"] == "planning"
    assert isinstance(agent.state["features"], list)

@pytest.mark.asyncio
async def test_process_request(agent):
    """Test processing a simple request."""
    request = "Create a hello world application"
    result = await agent.process_request(request)
    
    assert result["status"] == "success"
    assert "state" in result
    assert result["state"]["current_phase"] in ["planning", "implementing", "enhancing"]

@pytest.mark.asyncio
async def test_state_persistence(agent):
    """Test state persistence."""
    # Process a request
    request = "Create a simple calculator"
    result = await agent.process_request(request)
    
    # Verify state was saved
    state_file = PROJECT_ROOT / "memlog" / "project_state.json"
    assert state_file.exists()
    
    # Load and verify state
    saved_state = json.loads(state_file.read_text())
    assert saved_state["status"] == result["state"]["status"]
    assert saved_state["current_phase"] == result["state"]["current_phase"]

@pytest.mark.asyncio
async def test_history_tracking(agent):
    """Test development history tracking."""
    # Process a request
    request = "Create a todo list"
    await agent.process_request(request)
    
    # Get history
    history = agent.get_development_history()
    
    assert isinstance(history, list)
    assert len(history) > 0
    
    last_entry = history[-1]
    assert "action" in last_entry
    assert "timestamp" in last_entry
    assert "details" in last_entry

@pytest.mark.asyncio
async def test_tool_execution(agent):
    """Test that tools are properly initialized and can be executed."""
    assert len(agent.tools) > 0
    
    # Verify each tool type is present
    tool_names = [tool.tool.name for tool in agent.tools]
    assert any("generate_code" in name for name in tool_names)
    assert any("analyze_code" in name for name in tool_names)
    assert any("read_file" in name for name in tool_names)
    assert any("write_file" in name for name in tool_names)
    assert any("analyze_project_structure" in name for name in tool_names)

def test_error_handling(agent):
    """Test error handling with invalid requests."""
    with pytest.raises(Exception):
        asyncio.run(agent.process_request(""))  # Empty request should raise error

if __name__ == "__main__":
    pytest.main([__file__])
