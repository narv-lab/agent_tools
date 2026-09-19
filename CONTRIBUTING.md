# Contributing to Agent Tools

Thank you for your interest in the Agent Tools project!
We welcome contributors who want to help build a robust tool suite for autonomous LLM agents.

## Development Setup

This project uses `uv` for package and dependency management.

### Prerequisites
- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/)

### Installation Steps

1. Fork the repository and clone it locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/agent_tools.git
   cd agent_tools
   ```

2. Install all workspace packages and dependencies:
   ```bash
   uv sync --all-packages
   ```

## Development Workflow

### Branching Strategy
- When adding new features or fixing bugs, please create a new branch for your work (e.g., `feature/add-new-tool`, `fix/bug-name`).

### Coding Standards and Linting
- Please follow the existing coding conventions to keep the codebase readable and maintainable.
- A linter and formatter (e.g., Ruff) will be introduced in the future.

### Testing
Currently, the comprehensive test suite is a work in progress. Only a few core functionalities are covered by tests.
We highly encourage and appreciate contributors adding tests along with their new features or bug fixes.

To run the existing tests (if your environment is set up):
```bash
uv run pytest
```

## Pull Request Process

1. Commit your changes and push them to your branched fork.
2. Open a Pull Request against the `main` branch of this repository.
3. Clearly describe the purpose and context of your changes in the PR description, referencing any related issue numbers.
4. Address any feedback from the reviewers.

## Guidelines for Adding or Modifying MCP Tools

If you are adding a new tool or modifying an existing one, please adhere to the following design principles:

- **Safety First**: Destructive tools (e.g., editing, deleting) must provide a `dry_run` or validation mechanism to ensure the workspace is never left in a broken state.
- **Predictable Error Handling**: Instead of throwing raw exceptions for expected failures, return a structured result object (e.g., `ErrorResult`) so LLM agents can handle them reliably.
- **Idempotency**: File modifying operations should use idempotency keys to safely handle agent retries and prevent duplicate side effects.
- **Plugin Architecture**: Implement new tool packages as dynamically loaded modules using Python `entry-points`.

We look forward to your contributions!
