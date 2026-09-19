import mcp.types as types
from core.registry import MCPRegistry
from core.di_container import DIContainer
import json
import discovery

def register(registry: MCPRegistry, container: DIContainer):

    registry.register_tool(
        types.Tool(
            name="get_repo_map",
            description="Execute get_repo_map",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        lambda args: _handle_get_repo_map(args)
    )

    registry.register_tool(
        types.Tool(
            name="get_file_overview",
            description="Execute get_file_overview",
            inputSchema={
                "type": "object",
                "properties": {
    "FilePath": {
        "type": "string",
        "description": "FilePath parameter"
    }
},
                "required": ["FilePath"]
            }
        ),
        lambda args: _handle_get_file_overview(args)
    )

    registry.register_tool(
        types.Tool(
            name="get_symbol_content",
            description="Execute get_symbol_content",
            inputSchema={
                "type": "object",
                "properties": {
    "uri": {
        "type": "string",
        "description": "uri parameter"
    },
    "MaxLines": {
        "type": "integer",
        "description": "MaxLines parameter"
    }
},
                "required": ["uri", "MaxLines"]
            }
        ),
        lambda args: _handle_get_symbol_content(args)
    )

    registry.register_tool(
        types.Tool(
            name="read_symbol_lines",
            description="Execute read_symbol_lines",
            inputSchema={
                "type": "object",
                "properties": {
    "uri": {
        "type": "string",
        "description": "uri parameter"
    },
    "StartLine": {
        "type": "integer",
        "description": "StartLine parameter"
    },
    "EndLine": {
        "type": "integer",
        "description": "EndLine parameter"
    }
},
                "required": ["uri", "StartLine", "EndLine"]
            }
        ),
        lambda args: _handle_read_symbol_lines(args)
    )

    registry.register_tool(
        types.Tool(
            name="query_nodes",
            description="Execute query_nodes",
            inputSchema={
                "type": "object",
                "properties": {
    "QueryString": {
        "type": "string",
        "description": "QueryString parameter"
    },
    "MaxResults": {
        "type": "integer",
        "description": "MaxResults parameter"
    }
},
                "required": ["QueryString", "MaxResults"]
            }
        ),
        lambda args: _handle_query_nodes(args)
    )

    registry.register_tool(
        types.Tool(
            name="get_scope_context",
            description="Execute get_scope_context",
            inputSchema={
                "type": "object",
                "properties": {
    "uri": {
        "type": "string",
        "description": "uri parameter"
    }
},
                "required": ["uri"]
            }
        ),
        lambda args: _handle_get_scope_context(args)
    )

    registry.register_tool(
        types.Tool(
            name="resolve_symbol",
            description="Execute resolve_symbol",
            inputSchema={
                "type": "object",
                "properties": {
    "uri": {
        "type": "string",
        "description": "uri parameter"
    }
},
                "required": ["uri"]
            }
        ),
        lambda args: _handle_resolve_symbol(args)
    )

    registry.register_tool(
        types.Tool(
            name="find_references",
            description="Execute find_references",
            inputSchema={
                "type": "object",
                "properties": {
    "id": {
        "type": "string",
        "description": "id parameter"
    },
    "MaxResults": {
        "type": "integer",
        "description": "MaxResults parameter"
    },
    "Cursor": {
        "type": "string",
        "description": "Cursor parameter"
    }
},
                "required": ["id", "MaxResults"]
            }
        ),
        lambda args: _handle_find_references(args)
    )

    registry.register_tool(
        types.Tool(
            name="search_semantic",
            description="Execute search_semantic",
            inputSchema={
                "type": "object",
                "properties": {
    "NaturalLanguageQuery": {
        "type": "string",
        "description": "NaturalLanguageQuery parameter"
    },
    "MaxResults": {
        "type": "integer",
        "description": "MaxResults parameter"
    },
    "Cursor": {
        "type": "string",
        "description": "Cursor parameter"
    }
},
                "required": ["NaturalLanguageQuery", "MaxResults"]
            }
        ),
        lambda args: _handle_search_semantic(args)
    )

    registry.register_tool(
        types.Tool(
            name="search_structural",
            description="Execute search_structural",
            inputSchema={
                "type": "object",
                "properties": {
    "ASTPattern": {
        "type": "string",
        "description": "ASTPattern parameter"
    }
},
                "required": ["ASTPattern"]
            }
        ),
        lambda args: _handle_search_structural(args)
    )

    registry.register_tool(
        types.Tool(
            name="grep_workspace",
            description="Execute grep_workspace",
            inputSchema={
                "type": "object",
                "properties": {
    "RegexPattern": {
        "type": "string",
        "description": "RegexPattern parameter"
    },
    "MaxResults": {
        "type": "integer",
        "description": "MaxResults parameter"
    },
    "Cursor": {
        "type": "string",
        "description": "Cursor parameter"
    }
},
                "required": ["RegexPattern", "MaxResults"]
            }
        ),
        lambda args: _handle_grep_workspace(args)
    )


async def _handle_get_repo_map(args: dict) -> list[types.TextContent]:
    res = discovery.get_repo_map()
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_get_file_overview(args: dict) -> list[types.TextContent]:
    res = discovery.get_file_overview(args.get("FilePath"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_get_symbol_content(args: dict) -> list[types.TextContent]:
    res = discovery.get_symbol_content(args.get("uri"), args.get("MaxLines"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_read_symbol_lines(args: dict) -> list[types.TextContent]:
    res = discovery.read_symbol_lines(args.get("uri"), args.get("StartLine"), args.get("EndLine"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_query_nodes(args: dict) -> list[types.TextContent]:
    res = discovery.query_nodes(args.get("QueryString"), args.get("MaxResults"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_get_scope_context(args: dict) -> list[types.TextContent]:
    res = discovery.get_scope_context(args.get("uri"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_resolve_symbol(args: dict) -> list[types.TextContent]:
    res = discovery.resolve_symbol(args.get("uri"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_find_references(args: dict) -> list[types.TextContent]:
    res = discovery.find_references(args.get("id"), args.get("MaxResults"), args.get("Cursor"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_search_semantic(args: dict) -> list[types.TextContent]:
    res = discovery.search_semantic(args.get("NaturalLanguageQuery"), args.get("MaxResults"), args.get("Cursor"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_search_structural(args: dict) -> list[types.TextContent]:
    res = discovery.search_structural(args.get("ASTPattern"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_grep_workspace(args: dict) -> list[types.TextContent]:
    res = discovery.grep_workspace(args.get("RegexPattern"), args.get("MaxResults"), args.get("Cursor"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]
