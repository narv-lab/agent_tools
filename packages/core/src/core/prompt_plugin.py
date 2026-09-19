import os
import mcp.types as types
from typing import Any

def register_tools(registry: Any, container: Any):
    # Core tools could be registered here, but we use this to register prompts too.
    registry.register_prompt(
        types.Prompt(
            name="orchestrator_prompt",
            description="System prompt for orchestrating agent tool execution",
            arguments=[]
        ),
        _handle_orchestrator_prompt
    )

async def _handle_orchestrator_prompt(args):
    # Get project root from env or assume standard relative path
    workspace_root = os.environ.get("AGENT_WORKSPACE_CWD", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../../")))
    prompt_path = os.path.join(workspace_root, "prompts", "orchestrator_prompt.md")
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        content = "Error: orchestrator_prompt.md not found."

    return types.GetPromptResult(
        description="System prompt for orchestrating agent tool execution",
        messages=[
            types.PromptMessage(
                role="system",
                content=types.TextContent(type="text", text=content)
            )
        ]
    )
