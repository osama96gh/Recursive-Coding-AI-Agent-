# Memory Bank Structure

```mermaid
flowchart TD
    subgraph Core ["Core Documentation"]
        PB[projectbrief.md] --> PC[productContext.md]
        PB --> SP[systemPatterns.md]
        PB --> TC[techContext.md]
        
        PC --> AC[activeContext.md]
        SP --> AC
        TC --> AC
        
        AC --> Progress[progress.md]
    end
    
    subgraph Updates ["Documentation Updates"]
        Changes[Code Changes] --> StateUpdate[Update State]
        StateUpdate --> DocUpdate[Update Documentation]
        
        DocUpdate --> AC
        DocUpdate --> Progress
        
        subgraph Triggers ["Update Triggers"]
            NewPatterns[New Patterns]
            SignificantChanges[Significant Changes]
            UserRequest[User Request]
            ContextClarification[Context Clarification]
        end
        
        Triggers --> DocUpdate
    end
    
    subgraph Rules [".clinerules"]
        ProjectPatterns[Project Patterns]
        Implementation[Implementation Patterns]
        UserInteraction[User Interaction]
        Intelligence[Project Intelligence]
        
        ProjectPatterns --> Rules
        Implementation --> Rules
        UserInteraction --> Rules
        Intelligence --> Rules
        
        Rules[Project Rules] --> Development[Development Process]
    end
    
    Development --> Changes
```

This diagram illustrates the Memory Bank structure and documentation flow:

1. **Core Documentation**:
   - Project Brief as the foundation
   - Context documents build understanding
   - Active Context tracks current state
   - Progress monitors development

2. **Documentation Updates**:
   - Triggered by various events
   - Updates flow through state
   - Maintains system knowledge
   - Ensures consistency

3. **Project Rules**:
   - Captures patterns and preferences
   - Guides implementation
   - Defines interactions
   - Preserves intelligence

4. **Development Flow**:
   - Rules inform development
   - Changes trigger updates
   - Documentation stays current
   - Knowledge persists between sessions
