import mcp.types as types
from core.registry import MCPRegistry
from core.di_container import DIContainer
from .service import CollaborationService

def register(registry: MCPRegistry, container: DIContainer):
    service = CollaborationService()

    registry.register_tool(
        types.Tool(
            name="ask_human_sync",
            description="Ask a question to a human synchronously and wait for the response.",
            inputSchema={
                "type": "object",
                "properties": {
                    "Question": {"type": "string", "description": "The question to ask the human."}
                },
                "required": ["Question"]
            }
        ),
        lambda args: _handle_ask_human_sync(service, args)
    )

    registry.register_tool(
        types.Tool(
            name="ask_human_async",
            description="Ask a question to a human asynchronously. Returns a request ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "Question": {"type": "string", "description": "The question to ask the human."}
                },
                "required": ["Question"]
            }
        ),
        lambda args: _handle_ask_human_async(service, args)
    )

    registry.register_tool(
        types.Tool(
            name="check_human_response",
            description="Check the status of an asynchronous human request.",
            inputSchema={
                "type": "object",
                "properties": {
                    "RequestID": {"type": "string", "description": "The request ID to check."}
                },
                "required": ["RequestID"]
            }
        ),
        lambda args: _handle_check_human_response(service, args)
    )

    registry.register_tool(
        types.Tool(
            name="sync_workspace_state",
            description="Sync the workspace state to detect any external changes.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        lambda args: _handle_sync_workspace_state(service, args)
    )

async def _handle_ask_human_sync(service: CollaborationService, args: dict) -> list[types.TextContent]:
    res = service.ask_human_sync(args["Question"])
    return [types.TextContent(type="text", text=str(res))]

async def _handle_ask_human_async(service: CollaborationService, args: dict) -> list[types.TextContent]:
    res = service.ask_human_async(args["Question"])
    return [types.TextContent(type="text", text=str(res))]

async def _handle_check_human_response(service: CollaborationService, args: dict) -> list[types.TextContent]:
    res = service.check_human_response(args["RequestID"])
    return [types.TextContent(type="text", text=str(res))]

async def _handle_sync_workspace_state(service: CollaborationService, args: dict) -> list[types.TextContent]:
    res = service.sync_workspace_state()
    return [types.TextContent(type="text", text=str(res))]
