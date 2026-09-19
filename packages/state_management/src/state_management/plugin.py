import json
import mcp.types as types
from typing import Any
from state_management.manager import StateManager

def register_tools(registry: Any, container: Any):
    try:
        manager = container.resolve(StateManager)
    except ValueError:
        manager = StateManager()
        container.register(StateManager, manager)

    registry.register_tool(
        types.Tool(
            name="snapshot_workspace",
            description="Snapshot the workspace.",
            inputSchema={"type": "object", "properties": {}}
        ),
        lambda args: _handle_snapshot_workspace(manager, args)
    )

    registry.register_tool(
        types.Tool(
            name="restore_workspace",
            description="Restore the workspace.",
            inputSchema={"type": "object", "properties": {"CommitHash": {"type": "string"}}, "required": ["CommitHash"]}
        ),
        lambda args: _handle_restore_workspace(manager, args)
    )

async def _handle_snapshot_workspace(manager, args):
    try:
        res = manager.create_checkpoint()
        return [types.TextContent(type="text", text=json.dumps(res))]
    except Exception as e:
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]

async def _handle_restore_workspace(manager, args):
    try:
        manager.revert_to_checkpoint(args["CommitHash"], force=True)
        return [types.TextContent(type="text", text=json.dumps({"success": True, "error_reason": None}))]
    except Exception as e:
        return [types.TextContent(type="text", text=json.dumps({"success": False, "error_reason": str(e)}))]
