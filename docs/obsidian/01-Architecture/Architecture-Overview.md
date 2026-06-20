# Architecture Overview

> High-level system design and technical documentation for Flying Probe Copilot

## System Diagram

```
[User Input] → [API] → [Core Engine] → [Database] → [Analytics]
                          ↓
                    [Flying Probe Control]
```

## Key Components

### 1. Core Engine
- **Purpose**: Main processing logic
- **Technology**: Python
- **Responsibilities**:
  - Request processing
  - Validation
  - Business logic

### 2. API Layer
- **Purpose**: External interfaces
- **Type**: REST API
- **Endpoints**: [Link to API docs]

### 3. Flying Probe Interface
- **Purpose**: Hardware communication
- **Status**: [TODO]

### 4. Data Layer
- **Purpose**: Persistence
- **Database**: [TODO - Check CLAUDE.md]
- **Schema**: [TODO]

---

## Related Notes

- [[ADRs|Architecture Decision Records]] - Design decisions
- [[Technical-Stack|Technical Stack]] - Technology choices
- [[01-Architecture/Component-Details|Component Deep-Dives]]

## Last Updated
- Date: [TODO]
- Updated By: [TODO]
- Next Review: [TODO]

---

**Tags:** #architecture #core-system
