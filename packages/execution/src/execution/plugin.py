import mcp.types as types
from core.registry import MCPRegistry
from core.di_container import DIContainer
import json
from execution.service import ExecutionService
from execution.models import ErrorResult

# Singleton instance for the plugin
execution_service = ExecutionService()

def register(registry: MCPRegistry, container: DIContainer):
    try:
        container.register(ExecutionService, execution_service)
    except Exception:
        pass

    registry.register_tool(
        types.Tool(
            name="run_tests",
            description="Execute tests",
            inputSchema={
                "type": "object",
                "properties": {
                    "TestTarget": {"type": "string"},
                    "overrides": {"type": "object"}
                },
                "required": ["TestTarget"]
            }
        ),
        lambda args: _handle_run_tests(args)
    )

    registry.register_tool(
        types.Tool(
            name="execute_bash",
            description="Execute bash script",
            inputSchema={
                "type": "object",
                "properties": {
                    "Script": {"type": "string"},
                    "TimeoutMs": {"type": "integer"},
                    "profile": {"type": "object"},
                    "overrides": {"type": "object"}
                },
                "required": ["Script"]
            }
        ),
        lambda args: _handle_execute_bash(args)
    )
    
    registry.register_tool(
        types.Tool(
            name="spawn_process",
            description="Spawn process",
            inputSchema={
                "type": "object",
                "properties": {
                    "Command": {"type": "string"},
                    "UsePTY": {"type": "boolean"},
                    "profile": {"type": "object"},
                    "overrides": {"type": "object"}
                },
                "required": ["Command"]
            }
        ),
        lambda args: _handle_spawn_process(args)
    )

    registry.register_tool(
        types.Tool(
            name="read_process_output",
            description="Read process output",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "Offset": {"type": "integer"}
                },
                "required": ["process_id", "Offset"]
            }
        ),
        lambda args: _handle_read_process_output(args)
    )

    registry.register_tool(
        types.Tool(
            name="send_input_to_process",
            description="Send input to process",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"},
                    "Input": {"type": "string"}
                },
                "required": ["process_id", "Input"]
            }
        ),
        lambda args: _handle_send_input_to_process(args)
    )

    registry.register_tool(
        types.Tool(
            name="kill_process",
            description="Kill process",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_id": {"type": "string"}
                },
                "required": ["process_id"]
            }
        ),
        lambda args: _handle_kill_process(args)
    )

async def _handle_run_tests(args: dict) -> list[types.TextContent]:
    res = execution_service.run_tests(args.get("TestTarget"), args.get("overrides", {}))
    return _format_res(res)

async def _handle_execute_bash(args: dict) -> list[types.TextContent]:
    res = execution_service.execute_bash(args.get("Script"), args.get("TimeoutMs", 5000), args.get("profile"), args.get("overrides", {}))
    return _format_res(res)

async def _handle_spawn_process(args: dict) -> list[types.TextContent]:
    res = execution_service.spawn_process(args.get("Command"), args.get("UsePTY", False), args.get("profile"), args.get("overrides", {}))
    return _format_res(res)

async def _handle_read_process_output(args: dict) -> list[types.TextContent]:
    res = execution_service.read_process_output(args.get("process_id"), args.get("Offset", 0))
    return _format_res(res)

async def _handle_send_input_to_process(args: dict) -> list[types.TextContent]:
    res = execution_service.send_input_to_process(args.get("process_id"), args.get("Input"))
    return _format_res(res)

async def _handle_kill_process(args: dict) -> list[types.TextContent]:
    res = execution_service.kill_process(args.get("process_id"))
    return _format_res(res)

def _format_res(res) -> list[types.TextContent]:
    if isinstance(res, ErrorResult):
        # Typed serialization of L1 Error(Message: String) -- clients can identify it via the "error" key (FINDING-003)
        return [types.TextContent(type="text", text=json.dumps({"error": res.error}))]
    if isinstance(res, list):
        formatted = [r.__dict__ if hasattr(r, "__dict__") else r for r in res]
        return [types.TextContent(type="text", text=json.dumps(formatted))]
    if isinstance(res, dict):
        # Return other dict-type responses as JSON
        return [types.TextContent(type="text", text=json.dumps(res))]
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]
