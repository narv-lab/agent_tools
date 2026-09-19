from typing import Callable, Dict, Any, List, Awaitable
import mcp.types as types

ToolHandler = Callable[[dict], Awaitable[list[types.TextContent | types.ImageContent | types.EmbeddedResource]]]

class MCPRegistry:
    def __init__(self):
        self._tools: List[types.Tool] = []
        self._handlers: Dict[str, ToolHandler] = {}
        self._prompts: List[types.Prompt] = []
        self._prompt_handlers: Dict[str, Callable[[dict], Awaitable[types.GetPromptResult]]] = {}
        
    def register_tool(self, tool_def: types.Tool, handler: ToolHandler):
        """
        Register a new tool and its async handler.
        """
        self._tools.append(tool_def)
        self._handlers[tool_def.name] = handler
        
    def get_tools(self) -> List[types.Tool]:
        return self._tools
        
    async def call_tool(self, name: str, arguments: dict) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        handler = self._handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown tool or not yet registered: {name}")
        return await handler(arguments)

    def register_prompt(self, prompt_def: types.Prompt, handler: Callable[[dict], Awaitable[types.GetPromptResult]]):
        """
        Register a new prompt and its async handler.
        """
        self._prompts.append(prompt_def)
        self._prompt_handlers[prompt_def.name] = handler

    def get_prompts(self) -> List[types.Prompt]:
        return self._prompts

    async def get_prompt(self, name: str, arguments: dict) -> types.GetPromptResult:
        handler = self._prompt_handlers.get(name)
        if not handler:
            raise ValueError(f"Unknown prompt or not yet registered: {name}")
        return await handler(arguments)

# Global registry instance
registry = MCPRegistry()
