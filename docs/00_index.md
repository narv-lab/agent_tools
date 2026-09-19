# Agent Tools MCP Server — Design Document

> **Version**: 0.1.0  
> **Last Updated**: 2026-09-19  
> **Target Python**: ≥ 3.10

---

## Table of Contents

| # | Document | Overview |
|---|-------------|------|
| 01 | [System Overview](./01_system_overview.md) | Overall project architecture, design philosophy, and dependency maps |
| 02 | [core Package](./02_core.md) | DI container, MCPRegistry, exception hierarchy, logger, plugin loader |
| 03 | [discovery Package](./03_discovery.md) | Code exploration, tree-sitter AST parsing, TF-IDF semantic search, grep |
| 04 | [editing Package](./04_editing.md) | File operations, patch application/validation, dry-run, AST/Symbol replacement |
| 05 | [execution Package](./05_execution.md) | Bash execution, process management, test execution, PTY support |
| 06 | [state_management Package](./06_state_management.md) | Git checkpoints, snapshots, workspace restoration |
| 07 | [collaboration Package](./07_collaboration.md) | Human-agent collaboration, sync/async questions, workspace sync |

---

## Project Structure (Top-level)

```
agent_tools/
├── pyproject.toml              # Workspace root (uv workspace)
├── prompts/
│   └── orchestrator_prompt.md  # System prompt for orchestrator
├── packages/
│   ├── core/                   # Core/Foundation package
│   ├── discovery/              # Code discovery package
│   ├── editing/                # Code editing package
│   ├── execution/              # Command execution package
│   ├── state_management/       # State management package
│   └── collaboration/          # Collaboration package
├── tests/                      # Integration tests
└── docs/                       # Design documents (this directory)
```
