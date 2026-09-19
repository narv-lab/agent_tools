"""
Application entry point and MCP Server Foundation.
"""
import asyncio
import logging
import sys
import os
from importlib.metadata import entry_points
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from core.logger import get_logger
from core.di_container import DIContainer
from core.registry import registry

logger = get_logger(__name__)

container = DIContainer()

def load_plugins():
    """
    Dynamically discover and load MCP tools from installed packages using entry points.
    Each package should define an entry point under the group 'mcp.tools'.
    """
    logger.info("Discovering MCP tool plugins...")
    try:
        # Python 3.10+ way
        eps = entry_points(group="mcp.tools")
    except TypeError:
        # Fallback for older python if needed, though project requires >=3.10
        eps = entry_points().get("mcp.tools", [])

    for ep in eps:
        try:
            logger.info(f"Loading plugin: {ep.name} from {ep.value}")
            register_fn = ep.load()
            register_fn(registry, container)
        except Exception as e:
            logger.error(f"Failed to load plugin {ep.name}: {e}")

async def on_list_tools(ctx, params) -> types.ListToolsResult:
    logger.info("list_tools called")
    return types.ListToolsResult(tools=registry.get_tools())

async def on_call_tool(ctx, params) -> types.CallToolResult:
    logger.info(f"call_tool called for {params.name}")
    
    # Extract client workspace dynamically from MCP protocol or env var
    if not hasattr(app, "client_cwd"):
        try:
            if hasattr(ctx.session, "list_roots"):
                roots_result = await ctx.session.list_roots()
                if roots_result.roots:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(roots_result.roots[0].uri)
                    # If it's a file URI or no scheme, use the path
                    app.client_cwd = urllib.parse.unquote(parsed.path) if parsed.scheme in ('file', '') else roots_result.roots[0].uri
                    logger.info(f"Dynamically set AGENT_WORKSPACE_CWD to {app.client_cwd} from list_roots")
        except Exception as e:
            logger.warning(f"Could not fetch roots: {e}")
            
        if getattr(app, "client_cwd", None):
            os.environ["AGENT_WORKSPACE_CWD"] = app.client_cwd
        elif "AGENT_WORKSPACE_CWD" in os.environ:
            app.client_cwd = os.environ["AGENT_WORKSPACE_CWD"]
        else:
            # Fallback: Traverse process tree upwards to find client process (agy / antigravity) or ancestor with different CWD
            import subprocess
            pid = os.getpid()
            server_cwd = os.path.abspath(os.getcwd())
            client_cwd = None
            fallback_cwd = None

            while pid > 1:
                try:
                    ppid_out = subprocess.check_output(["ps", "-o", "ppid=", "-p", str(pid)], stderr=subprocess.DEVNULL).decode().strip()
                    if not ppid_out:
                        break
                    ppid = int(ppid_out)
                    if ppid <= 1 or ppid == pid:
                        break

                    cmd = subprocess.check_output(["ps", "-o", "command=", "-p", str(ppid)], stderr=subprocess.DEVNULL).decode().strip()
                    ppid_cwd = None

                    # Try lsof (macOS)
                    try:
                        cwd_out = subprocess.check_output(["lsof", "-a", "-p", str(ppid), "-d", "cwd", "-n", "-Fn"], stderr=subprocess.DEVNULL).decode()
                        for line in cwd_out.splitlines():
                            if line.startswith("n"):
                                ppid_cwd = line[1:].strip()
                                break
                    except Exception:
                        pass

                    # Try pwdx / /proc/<ppid>/cwd (Linux)
                    if not ppid_cwd:
                        try:
                            if os.path.exists(f"/proc/{ppid}/cwd"):
                                ppid_cwd = os.readlink(f"/proc/{ppid}/cwd")
                            else:
                                out = subprocess.check_output(["pwdx", str(ppid)], stderr=subprocess.DEVNULL).decode()
                                ppid_cwd = out.split(":", 1)[1].strip()
                        except Exception:
                            pass

                    if ppid_cwd and os.path.exists(ppid_cwd):
                        cmd_lower = cmd.lower()
                        if "agy" in cmd_lower or "antigravity" in cmd_lower:
                            client_cwd = ppid_cwd
                            logger.info(f"Found client process (PID {ppid}: {cmd}) with CWD: {client_cwd}")
                            break
                        if fallback_cwd is None and os.path.abspath(ppid_cwd) != server_cwd:
                            fallback_cwd = ppid_cwd

                    pid = ppid
                except Exception as e:
                    logger.debug(f"Error while traversing process tree at PID {pid}: {e}")
                    break

            resolved_cwd = client_cwd or fallback_cwd
            if resolved_cwd:
                app.client_cwd = resolved_cwd
                os.environ["AGENT_WORKSPACE_CWD"] = resolved_cwd
                logger.info(f"Dynamically set AGENT_WORKSPACE_CWD to {app.client_cwd} from process tree")

        if getattr(app, "client_cwd", None):
            try:
                os.chdir(app.client_cwd)
                logger.info(f"Changed CWD to {app.client_cwd}")
            except Exception as e:
                logger.error(f"Failed to change CWD to {app.client_cwd}: {e}")

    try:
        content = await registry.call_tool(params.name, params.arguments)
        return types.CallToolResult(content=content)
    except Exception as e:
        logger.error(f"Error calling tool {params.name}: {e}", exc_info=True)
        return types.CallToolResult(
            is_error=True,
            content=[types.TextContent(type="text", text=f"Tool execution failed: {str(e)}")]
        )

async def on_list_prompts(ctx, params) -> types.ListPromptsResult:
    logger.info("list_prompts called")
    return types.ListPromptsResult(prompts=registry.get_prompts())

async def on_get_prompt(ctx, params) -> types.GetPromptResult:
    logger.info(f"get_prompt called for {params.name}")
    return await registry.get_prompt(params.name, params.arguments or {})

app = Server(
    "agent-tools-mcp-server",
    on_list_tools=on_list_tools,
    on_call_tool=on_call_tool,
    on_list_prompts=on_list_prompts,
    on_get_prompt=on_get_prompt,
)

async def main():
    logger.info("SWE-bench Agent Tool System (MCP Server) starting.")
    load_plugins()
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())
