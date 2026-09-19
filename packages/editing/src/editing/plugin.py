import mcp.types as types
from core.registry import MCPRegistry
from core.di_container import DIContainer
import json
import editing

def register(registry: MCPRegistry, container: DIContainer):

    registry.register_tool(
        types.Tool(
            name="create_file",
            description="Execute create_file",
            inputSchema={
                "type": "object",
                "properties": {
    "file_path": {
        "type": "string",
        "description": "file_path parameter"
    },
    "initial_content": {
        "type": "string",
        "description": "initial_content parameter"
    },
    "idempotency_key": {
        "type": "string",
        "description": "idempotency_key parameter"
    }
},
                "required": ["file_path", "initial_content", "idempotency_key"]
            }
        ),
        lambda args: _handle_create_file(args)
    )

    registry.register_tool(
        types.Tool(
            name="delete_file",
            description="Execute delete_file",
            inputSchema={
                "type": "object",
                "properties": {
    "file_path": {
        "type": "string",
        "description": "file_path parameter"
    },
    "idempotency_key": {
        "type": "string",
        "description": "idempotency_key parameter"
    }
},
                "required": ["file_path", "idempotency_key"]
            }
        ),
        lambda args: _handle_delete_file(args)
    )

    registry.register_tool(
        types.Tool(
            name="move_file",
            description="Execute move_file",
            inputSchema={
                "type": "object",
                "properties": {
    "old_path": {
        "type": "string",
        "description": "old_path parameter"
    },
    "new_path": {
        "type": "string",
        "description": "new_path parameter"
    },
    "idempotency_key": {
        "type": "string",
        "description": "idempotency_key parameter"
    }
},
                "required": ["old_path", "new_path", "idempotency_key"]
            }
        ),
        lambda args: _handle_move_file(args)
    )

    registry.register_tool(
        types.Tool(
            name="apply_and_validate_patches",
            description="Execute apply_and_validate_patches",
            inputSchema={
                "type": "object",
                "properties": {
    "patches": {
        "type": "array",
        "description": "List of FilePatch objects. Each FilePatch must contain 'file_path' (string), 'intent' (string), and 'patches' (array of Patch objects). A Patch object must contain a 'target' object. Target can be SearchReplaceTarget (requires 'old_text', 'new_text', 'fuzzy_match'), ASTNodeTarget (requires 'node_uri', 'new_content'), UnifiedDiffTarget (requires 'diff_text'), SymbolTarget (requires 'uri', 'replacement'), or AppendTarget (requires 'uri', 'replacement', 'type'='AppendTarget').",
        "items": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "intent": {"type": "string"},
                "patches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "object"}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["file_path", "intent", "patches"]
        }
    },
    "auto_format": {
        "type": "boolean",
        "description": "auto_format parameter"
    },
    "idempotency_key": {
        "type": "string",
        "description": "idempotency_key parameter"
    }
},
                "required": ["patches", "auto_format", "idempotency_key"]
            }
        ),
        lambda args: _handle_apply_and_validate_patches(args)
    )

    registry.register_tool(
        types.Tool(
            name="dry_run_patches",
            description="Execute dry_run_patches",
            inputSchema={
                "type": "object",
                "properties": {
    "patches": {
        "type": "array",
        "description": "List of FilePatch objects. Each FilePatch must contain 'file_path' (string), 'intent' (string), and 'patches' (array of Patch objects). A Patch object must contain a 'target' object. Target can be SearchReplaceTarget (requires 'old_text', 'new_text', 'fuzzy_match'), ASTNodeTarget (requires 'node_uri', 'new_content'), UnifiedDiffTarget (requires 'diff_text'), SymbolTarget (requires 'uri', 'replacement'), or AppendTarget (requires 'uri', 'replacement', 'type'='AppendTarget').",
        "items": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "intent": {"type": "string"},
                "patches": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "target": {"type": "object"}
                        },
                        "required": ["target"]
                    }
                }
            },
            "required": ["file_path", "intent", "patches"]
        }
    }
},
                "required": ["patches"]
            }
        ),
        lambda args: _handle_dry_run_patches(args)
    )

    registry.register_tool(
        types.Tool(
            name="wait_for_diagnostics",
            description="Execute wait_for_diagnostics",
            inputSchema={
                "type": "object",
                "properties": {
    "timeout_ms": {
        "type": "integer",
        "description": "timeout_ms parameter"
    }
},
                "required": ["timeout_ms"]
            }
        ),
        lambda args: _handle_wait_for_diagnostics(args)
    )

    registry.register_tool(
        types.Tool(
            name="restart_lsp",
            description="Execute restart_lsp",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        lambda args: _handle_restart_lsp(args)
    )

    registry.register_tool(
        types.Tool(
            name="clear_cache_and_rebuild",
            description="Execute clear_cache_and_rebuild",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        lambda args: _handle_clear_cache_and_rebuild(args)
    )


async def _handle_create_file(args: dict) -> list[types.TextContent]:
    res = editing.create_file(args.get("file_path"), args.get("initial_content"), args.get("idempotency_key"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_delete_file(args: dict) -> list[types.TextContent]:
    res = editing.delete_file(args.get("file_path"), args.get("idempotency_key"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_move_file(args: dict) -> list[types.TextContent]:
    res = editing.move_file(args.get("old_path"), args.get("new_path"), args.get("idempotency_key"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


import dataclasses

def _parse_file_patches(patches_data: list) -> list[editing.FilePatch]:
    if not patches_data:
        return []
    parsed = []
    for fp_data in patches_data:
        patches = []
        for p_data in fp_data.get("patches", []):
            t_data = p_data.get("target", {})
            target = None
            if "old_text" in t_data and "new_text" in t_data:
                target = editing.SearchReplaceTarget(
                    old_text=t_data.get("old_text", ""),
                    new_text=t_data.get("new_text", ""),
                    fuzzy_match=t_data.get("fuzzy_match", False)
                )
            elif "node_uri" in t_data and "new_content" in t_data:
                target = editing.ASTNodeTarget(
                    node_uri=t_data.get("node_uri", ""),
                    new_content=t_data.get("new_content", "")
                )
            elif "diff_text" in t_data:
                target = editing.UnifiedDiffTarget(
                    diff_text=t_data.get("diff_text", "")
                )
            elif "uri" in t_data and "replacement" in t_data:
                if t_data.get("type") == "AppendTarget":
                    target = editing.AppendTarget(uri=t_data["uri"], replacement=t_data["replacement"])
                else:
                    target = editing.SymbolTarget(uri=t_data["uri"], replacement=t_data["replacement"])
            
            if target:
                patches.append(editing.Patch(target=target))
            else:
                raise ValueError(f"Invalid or unrecognized patch target format: {t_data}")
                
        if not patches:
            raise ValueError(f"No valid patches found in FilePatch for {fp_data.get('file_path')}")
                
        parsed.append(editing.FilePatch(
            file_path=fp_data.get("file_path", ""),
            intent=fp_data.get("intent", ""),
            patches=patches
        ))
    return parsed

async def _handle_apply_and_validate_patches(args: dict) -> list[types.TextContent]:
    patches_data = args.get("patches", [])
    parsed_patches = _parse_file_patches(patches_data)
    res = editing.apply_and_validate_patches(parsed_patches, args.get("auto_format", False), args.get("idempotency_key", ""))
    try:
        if dataclasses.is_dataclass(res):
            return [types.TextContent(type="text", text=json.dumps(dataclasses.asdict(res)))]
        elif hasattr(res, "__dict__"):
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
    except Exception:
        pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_dry_run_patches(args: dict) -> list[types.TextContent]:
    patches_data = args.get("patches", [])
    parsed_patches = _parse_file_patches(patches_data)
    res = editing.dry_run_patches(parsed_patches)
    try:
        if dataclasses.is_dataclass(res):
            return [types.TextContent(type="text", text=json.dumps(dataclasses.asdict(res)))]
        elif hasattr(res, "__dict__"):
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
    except Exception:
        pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_wait_for_diagnostics(args: dict) -> list[types.TextContent]:
    res = editing.wait_for_diagnostics(args.get("timeout_ms"))
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_restart_lsp(args: dict) -> list[types.TextContent]:
    res = editing.restart_lsp()
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]


async def _handle_clear_cache_and_rebuild(args: dict) -> list[types.TextContent]:
    res = editing.clear_cache_and_rebuild()
    if hasattr(res, "__dict__"):
        try:
            return [types.TextContent(type="text", text=json.dumps(res.__dict__))]
        except Exception:
            pass
    return [types.TextContent(type="text", text=str(res))]
