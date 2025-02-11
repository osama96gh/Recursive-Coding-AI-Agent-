# System Architecture

```mermaid
flowchart TD
    User[User/Client] --> Main[main.py]
    
    subgraph Core ["Core Components"]
        Main --> Workflow[AI Workflow]
        Workflow --> Agents[Agents]
        
        subgraph Agents ["Agent Types"]
            BaseAgent[Base Agent] --> SpecializedAgents[Specialized Agents]
            SpecializedAgents --> CodeGen[Code Generation Agent]
            SpecializedAgents --> ReqAgent[Requirement Agent]
            SpecializedAgents --> TestAgent[Testing Agent]
        end
        
        subgraph Tools ["Agent Tools"]
            CodeTools[Code Tools]
            FileTools[File Tools]
            FeedbackTools[Feedback Tools]
            ProjectTools[Project Tools]
            OutputValidator[Output Validator]
            PromptGen[Prompt Generator]
        end
        
        Agents --> Tools
    end
    
    subgraph State ["State Management"]
        StateSchema[State Schema]
        ProjectState[Project State]
        DevHistory[Development History]
    end
    
    Main --> State
    Workflow --> State
    Tools --> State
```

This diagram illustrates the high-level architecture of the Recursive Development Agent system:

1. **Entry Point**: `main.py` serves as the system entry point
2. **Core Components**:
   - AI Workflow orchestrates the development process
   - Agents (base and specialized) handle specific tasks
   - Various tools provide core functionality
3. **State Management**:
   - Maintains project state and development history
   - Schema defines state structure
4. **Tool Integration**:
   - Tools are used by agents for specific operations
   - Each tool category serves distinct purposes
