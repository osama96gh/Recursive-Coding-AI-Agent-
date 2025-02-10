"""Recursive workflow implementation using LangGraph."""
from typing import Dict, List, Optional, Annotated, TypedDict
import json
import logging
from datetime import datetime

from langgraph.graph import Graph, StateGraph, END

# Set up logging
logger = logging.getLogger(__name__)
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.agents.structured_chat.base import StructuredChatAgent
from langchain_core.tools import BaseTool

from ..agents.tools.code_tools import CodeTools
from ..agents.tools.file_tools import FileTools
from ..agents.tools.project_tools import ProjectTools
from ..config import PROJECT_ROOT

class ProjectState(TypedDict):
    """Type definition for project state."""
    status: str
    current_phase: str
    features: List[Dict]
    messages: List[Dict]
    next_steps: List[str]
    tools_output: Dict

from langchain_core.runnables import RunnablePassthrough, RunnableLambda

def create_recursive_workflow(llm, tool_executor: ToolExecutor) -> Graph:
    """Create the recursive development workflow."""
    from langchain.agents import AgentType, initialize_agent
    from langgraph.graph import StateGraph, END
    
    # Create the system message
    system_message = """You are a recursive development agent.
You have access to the following tools:

{tools}

Tool Schemas:

1. Code Tools:
   - generate_code:
     * type: string (required, e.g., "project_structure", "component", "api")
     * requirements: list of strings (required)
     * context: optional dict
     Example:
     ```
     {
       "action": "generate_code",
       "action_input": {
         "type": "project_structure",
         "requirements": [
           "Create a new Python game project",
           "Set up the main game loop",
           "Add player movement"
         ],
         "context": {
           "language": "python",
           "framework": "pygame"
         }
       }
     }
     ```
     Note: The type, requirements, and context must be passed directly in action_input, not nested further.
   - analyze_code:
     * code: string (required)
     * context: optional dict

2. File Tools:
   - read_file:
     * path: string
   - write_file:
     * path: string
     * content: string
   - list_directory:
     * path: string (default: ".")
     * recursive: optional bool (default: false)
   - delete_path:
     * path: string

3. Project Tools:
   - analyze_project_structure:
     * path: string (default: ".")
   - suggest_improvements:
     * analysis: dict

4. Feedback Tools:
   - ask_human:
     * question: string (to ask for clarification or feedback)

CRITICAL INSTRUCTION:
Your very first action for ANY task MUST be to use the ask_human tool to get requirements.
DO NOT proceed with any other actions or analysis until you get user input.

Example - when asked to build an app, your ONLY valid first response is:
{
  "action": "ask_human",
  "action_input": {
    "question": "To help build this app, please specify:\n1. Preferred technology stack (e.g., Python/Django, Node.js/Express)\n2. Core features needed\n3. Any specific requirements or constraints"
  }
}

After getting user requirements:
1. Use analyze_project_structure to check current state
2. Use generate_code with proper schema:
   {
     "action": "generate_code",
     "action_input": {
       "type": "project_structure",
       "requirements": ["requirement1", "requirement2"],
       "context": {"language": "python"}
     }
   }
3. Use write_file to implement the generated code
4. Use analyze_code to verify the implementation

ANY response that doesn't start with ask_human is INCORRECT.
DO NOT provide explanations or analysis without first getting user requirements.

Always take concrete actions using the tools rather than just providing analysis.
Format your tool calls exactly according to these schemas.

Example ask_human usage:
{
  "action": "ask_human",
  "action_input": {
    "question": "What specific features would you like in the game?"
  }
}"""

    # Create the agent with custom message creation
    def create_messages(input: str, chat_history: List[Dict]) -> List[Dict]:
        """Create messages in a serializable format."""
        messages = [{
            "type": "system",
            "content": system_message.format(tools=str(tool_executor.tools))
        }]
        
        # Add chat history
        for msg in chat_history:
            messages.append({
                "type": msg["type"],
                "content": msg["content"]
            })
        
        # Add current input
        messages.append({
            "type": "human",
            "content": input
        })
        
        # Convert to LangChain message objects
        return [
            SystemMessage(content=msg["content"]) if msg["type"] == "system"
            else HumanMessage(content=msg["content"]) if msg["type"] == "human"
            else AIMessage(content=msg["content"])
            for msg in messages
        ]
    
    # Create the agent with proper function calling configuration
    tools = tool_executor.tools
    
    # Create the agent
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message.format(tools=str(tools))),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}")
    ])

    agent = StructuredChatAgent(
        llm=llm,
        prompt=prompt,
        tools=tools,
        verbose=True
    )

    # Create the executor
    agent_executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True,
        max_iterations=10
    )
    
    def process_state(state: Dict) -> Dict:
        """Process state and prepare input for agent."""
        if not isinstance(state, dict):
            return {"input": "", "chat_history": []}
        
        messages = state.get("messages", [])
        if not messages:
            return {"input": "", "chat_history": []}
        
        # Convert messages to chat history format
        chat_history = []
        for msg in messages[:-1]:  # All messages except the last one
            content = msg.get("content", "")
            if msg.get("role") == "user":
                chat_history.append({"type": "human", "content": content})
            elif msg.get("role") == "assistant":
                chat_history.append({"type": "ai", "content": content})
        
        # Get the last message as input
        last_message = messages[-1]
        current_input = last_message.get("content", "") if last_message else ""
        
        return {
            "input": current_input,
            "chat_history": chat_history
        }
    
    def update_state(state: ProjectState, result: Dict) -> ProjectState:
        """Update state with agent result."""
        state["current_result"] = result.get("output", result)
        state["messages"].append({
            "role": "assistant",
            "content": str(result.get("output", result)),
            "timestamp": str(datetime.datetime.now())
        })
        return state
    
    # Create the workflow chain
    def prepare_input(input_dict: Dict) -> Dict:
        """Prepare input for the workflow."""
        state = input_dict.get("state", {})
        if not isinstance(state, dict):
            state = {}
        if "messages" not in state:
            state["messages"] = []
        state["messages"].append({
            "role": "user",
            "content": input_dict.get("input", ""),
            "timestamp": str(datetime.now())
        })
        return state

    def prepare_agent_input(state_dict: Dict) -> Dict:
        """Prepare input for the agent executor."""
        logger.debug(f"Preparing agent input from state: {state_dict}")
        processed = process_state(state_dict)
        logger.debug(f"Processed state: {processed}")
        messages = create_messages(processed["input"], processed["chat_history"])
        logger.debug(f"Created messages: {messages}")
        prepared_input = {
            "messages": messages,
            "input": processed["input"]
        }
        logger.debug(f"Final prepared input: {prepared_input}")
        return prepared_input

    def format_agent_output(output: Dict) -> Dict:
        """Format the agent's output into a consistent structure."""
        try:
            logger.debug(f"Formatting agent output: {output}")
            
            # Handle AgentExecutor output format
            if isinstance(output, dict):
                # Case 1: Standard AgentExecutor output
                if "output" in output and "intermediate_steps" in output:
                    steps = output.get("intermediate_steps", [])
                    
                    # If there are steps, use the last action
                    if steps and isinstance(steps[-1], tuple) and len(steps[-1]) >= 2:
                        action = steps[-1][0]
                        if isinstance(action, dict) and "tool" in action and "tool_input" in action:
                            return {
                                "output": {
                                    "action": action["tool"],
                                    "action_input": action["tool_input"]
                                }
                            }
                    
                    # If no valid steps or action, use the final output
                    return {
                        "output": {
                            "type": "response",
                            "content": str(output.get("output", ""))
                        }
                    }
                
                # Case 2: Direct output with action
                if "action" in output:
                    return {"output": output}
                
                # Case 3: Already formatted output
                if "output" in output and isinstance(output["output"], dict):
                    return output
                
                # Case 4: Raw output
                if "output" in output:
                    return {
                        "output": {
                            "type": "response",
                            "content": str(output["output"])
                        }
                    }
            
            # Default case: wrap as response
            return {
                "output": {
                    "type": "response",
                    "content": str(output)
                }
            }
            
        except Exception as e:
            error_msg = f"Error formatting output: {str(e)}\nOutput was: {str(output)}"
            logger.error(error_msg)
            return {
                "output": {
                    "type": "error",
                    "content": error_msg
                }
            }

    # Add logging to track agent output
    def log_agent_output(output: Dict) -> Dict:
        """Log the agent's output before formatting."""
        logger.debug(f"Raw agent output: {output}")
        formatted = format_agent_output(output)
        logger.debug(f"Formatted output: {formatted}")
        return formatted

    # Create the graph
    workflow = StateGraph(ProjectState)

    # Define nodes
    def process_input(state):
        """Process the input and prepare state."""
        state = prepare_input(state)
        return state

    async def execute_agent(state):
        """Execute the agent with the current state."""
        try:
            agent_input = prepare_agent_input(state)
            result = await agent_executor.ainvoke(agent_input)
            logger.debug(f"Raw agent result: {result}")
            
            # Extract the actual output from the agent result
            if isinstance(result, dict):
                if "output" in result:
                    output = result["output"]
                    if isinstance(output, str):
                        # Convert string output to structured format
                        try:
                            parsed = json.loads(output)
                            state["current_result"] = parsed
                        except json.JSONDecodeError:
                            state["current_result"] = {
                                "type": "response",
                                "content": output
                            }
                    else:
                        state["current_result"] = output
                elif "intermediate_steps" in result and result["intermediate_steps"]:
                    # Get the last action from intermediate steps
                    last_step = result["intermediate_steps"][-1]
                    if isinstance(last_step, tuple) and len(last_step) >= 2:
                        action = last_step[0]
                        if isinstance(action, dict):
                            state["current_result"] = {
                                "action": action.get("tool", ""),
                                "action_input": action.get("tool_input", {})
                            }
                
                # Add to messages if appropriate
                if "current_result" in state:
                    current_result = state["current_result"]
                    if isinstance(current_result, dict):
                        if current_result.get("type") == "response":
                            state["messages"].append({
                                "role": "assistant",
                                "content": current_result["content"],
                                "timestamp": str(datetime.now())
                            })
                        elif current_result.get("action") == "ask_human":
                            pass  # Don't add ask_human actions to messages
                        else:
                            state["messages"].append({
                                "role": "assistant",
                                "content": json.dumps(current_result, indent=2),
                                "timestamp": str(datetime.now())
                            })
            
            return state
            
        except Exception as e:
            logger.error(f"Agent execution error: {str(e)}")
            state["error"] = str(e)
            return state

    def should_continue(state):
        """Determine if we should continue processing."""
        # End if there's an error
        if "error" in state:
            return False
        
        # End if we have a final response
        result = state.get("current_result", {})
        if isinstance(result, dict):
            if result.get("type") == "response" and any(
                word in result.get("content", "").lower()
                for word in ["finished", "complete", "done", "quit"]
            ):
                return False
        
        return True

    # Add nodes
    workflow.add_node("process_input", process_input)
    workflow.add_node("execute_agent", execute_agent)

    # Add edges
    workflow.add_edge("process_input", "execute_agent")
    workflow.add_conditional_edges(
        "execute_agent",
        should_continue,
        {
            True: "execute_agent",  # Continue processing
            False: END  # End the workflow
        }
    )

    # Set entry point
    workflow.set_entry_point("process_input")

    return workflow.compile()

def initialize_project_state() -> ProjectState:
    """Initialize the project state."""
    return ProjectState(
        status="initialized",
        current_phase="planning",
        features=[],
        messages=[],
        next_steps=[],
        tools_output={}
    )
