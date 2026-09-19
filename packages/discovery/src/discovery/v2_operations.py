import os
import ast
from typing import Optional, List

from .types import (
    GuardedString, GuardedList, PaginatedText, ScopeInfo,
    FileOverview, ErrorResult, GuardedListResult, Node, GrepMatch, NodeTarget
)
from .operations import (
    get_repo_map as v1_get_repo_map,
    search_code as v1_search_code,
    semantic_search as v1_semantic_search,
    view_file as v1_view_file,
    view_symbol as v1_view_symbol,
    _get_ts_parser
)
from .exceptions import DiscoveryError

def _get_cwd() -> str:
    cwd = os.environ.get("AGENT_WORKSPACE_CWD", os.getcwd())
    return cwd

def get_repo_map() -> GuardedString:
    cwd = _get_cwd()
    try:
        # Default depth to 3 for v2
        result = v1_get_repo_map(cwd, 3)
        if len(result) > 10000:
            result = result[:10000] + "\n... [TRUNCATED]"
        return result
    except DiscoveryError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
def get_file_overview(FilePath: str) -> FileOverview | ErrorResult:
    cwd = _get_cwd()
    
    abs_path = os.path.join(cwd, FilePath) if not os.path.isabs(FilePath) else FilePath
    if not os.path.exists(abs_path):
        return {"error": f"File not found: {FilePath} (resolved to {abs_path})"}
    
    ext = os.path.splitext(abs_path)[1].lower()

    # --- Python: ast module parsing ---
    if ext == ".py":
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                code = f.read()
                
            tree = ast.parse(code)
            exports = []
            deps = []
            skeleton_lines = []
            
            for node in tree.body:
                if isinstance(node, ast.Import):
                    for alias in node.names: deps.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module: deps.append(node.module)
                elif isinstance(node, ast.ClassDef):
                    exports.append(f"{FilePath}#{node.name}")
                    skeleton_lines.append(f"class {node.name}:")
                    for sub in node.body:
                        if isinstance(sub, ast.FunctionDef):
                            skeleton_lines.append(f"    def {sub.name}(...):")
                elif isinstance(node, ast.FunctionDef):
                    exports.append(f"{FilePath}#{node.name}")
                    skeleton_lines.append(f"def {node.name}(...):")
                    
            return {
                "skeleton": "\n".join(skeleton_lines) or f"No structural elements found in {FilePath}",
                "exports": exports,
                "dependencies": list(set(deps))
            }
        except Exception as e:
            return {"error": f"Failed to parse {FilePath}: {str(e)}"}

    # --- Structured document: Try tree-sitter parsing, fallback to text on failure ---
    # (CHANGE-agent_tools_supported_languages-20260814-234500: Extension via PO exception)
    parser = _get_ts_parser(abs_path)
    if parser:
        try:
            with open(abs_path, "rb") as f:
                raw = f.read()
            ts_tree = parser.parse(raw)
            code_str = raw.decode("utf-8", errors="replace")
            exports = []
            skeleton_lines = []

            # 構造化ドキュメントのノード種別に応じたシンボル抽出
            _STRUCTURED_DOC_NODE_TYPES = {
                # JSON: プロパティキー
                "pair", "property",
                # YAML: マッピングキー
                "block_mapping_pair", "flow_pair",
                # Markdown: heading
                "atx_heading", "setext_heading",
                # HTML/XML: tag name
                "tag_name", "element",
                # CSS/SCSS: selector, rule
                "rule_set", "class_selector", "id_selector",
            }

            def extract_structured_symbols(node, depth=0):
                if node.type in _STRUCTURED_DOC_NODE_TYPES:
                    name_node = (
                        node.child_by_field_name("key")
                        or node.child_by_field_name("name")
                        or node.children[0] if node.children else None
                    )
                    if name_node:
                        name_text = raw[name_node.start_byte:name_node.end_byte].decode("utf-8", errors="replace").strip('"\'')
                        if name_text:
                            exports.append(f"{FilePath}#{name_text}")
                            skeleton_lines.append("  " * depth + name_text)
                for child in node.children:
                    extract_structured_symbols(child, depth + 1)

            extract_structured_symbols(ts_tree.root_node)

            return {
                "skeleton": "\n".join(skeleton_lines[:50]) or f"Parsed {ext} document: {FilePath}",
                "exports": exports[:30],
                "dependencies": []
            }
        except Exception:
            # tree-sitter parsing failure: Text fallback (L1 Design: fallback to text base on AST failure)
            pass

    # --- Text fallback: Return only basic info ---
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        return {
            "skeleton": f"[Text fallback] AST parsing not supported or yielded no structure for {ext}. Please use get_symbol_content (e.g. without #symbol) or read_symbol_lines to read the full file. File has {len(lines)} lines.",
            "exports": [],
            "dependencies": []
        }
    except Exception as e:
        return {"error": str(e)}


def get_symbol_content(uri: str, MaxLines: int) -> PaginatedText | ErrorResult:
    try:
        # Assuming uri format like "filepath#symbol" or just "filepath"
        if "#" in uri:
            filepath, symbol = uri.split("#", 1)
            # Remove "function:" etc prefix if present
            if ":" in symbol:
                symbol = symbol.split(":", 1)[1]
            cwd = _get_cwd()
            abs_path = os.path.join(cwd, filepath) if not os.path.isabs(filepath) else filepath
            content = v1_view_symbol(abs_path, symbol)
        else:
            filepath = uri
            cwd = _get_cwd()
            abs_path = os.path.join(cwd, filepath) if not os.path.isabs(filepath) else filepath
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

        # Handle truncation manually
        lines = content.split('\n')
        is_truncated = len(lines) > MaxLines
        content_str = "\n".join(lines[:MaxLines])
        return {"content": content_str, "is_truncated": is_truncated, "next_line": MaxLines + 1 if is_truncated else None}
    except DiscoveryError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def read_symbol_lines(uri: str, StartLine: int, EndLine: int) -> PaginatedText | ErrorResult:
    if uri is None:
        return {"error": "Missing required parameter: uri"}
    try:
        filepath = uri.split("#")[0] if "#" in uri else uri
        cwd = _get_cwd()
        abs_path = os.path.join(cwd, filepath) if not os.path.isabs(filepath) else filepath
        content = v1_view_file(abs_path, StartLine, EndLine)
        return {"content": content, "is_truncated": False, "next_line": None}
    except DiscoveryError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def query_nodes(QueryString: str, MaxResults: int) -> GuardedList:
    cwd = _get_cwd()
    try:
        output = v1_search_code(QueryString, True, cwd)
        lines = output.split('\n') if output else []
        matches = []
        for line in lines[:MaxResults]:
            parts = line.split(":", 2)
            if len(parts) >= 2:
                file_path = parts[0]
                matches.append({"uri": f"{file_path}#{QueryString}", "type": "match"})
        
        next_cursor = str(MaxResults) if len(lines) > MaxResults else None
        return {"results": matches, "next_cursor": next_cursor}
    except DiscoveryError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def get_scope_context(uri: str) -> ScopeInfo | ErrorResult:
    try:
        filepath = uri.split("#")[0] if "#" in uri else uri
        cwd = _get_cwd()
        abs_path = os.path.join(cwd, filepath) if not os.path.isabs(filepath) else filepath
        
        parser = _get_ts_parser(abs_path)
        signatures = []
        if parser and os.path.exists(abs_path):
            with open(abs_path, 'rb') as f:
                code = f.read()
            tree = parser.parse(code)
            def traverse(node):
                if node.type in ('function_definition', 'class_definition', 'method_definition'):
                    name_node = node.child_by_field_name('name')
                    if name_node:
                        name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                        signatures.append(f"{node.type}: {name}")
                for child in node.children:
                    traverse(child)
            traverse(tree.root_node)
        return signatures
    except Exception as e:
        return {"error": str(e)}

def resolve_symbol(uri: str) -> GuardedString:
    try:
        if "#" in uri:
            filepath, symbol = uri.split("#", 1)
            if ":" in symbol:
                symbol = symbol.split(":", 1)[1]
            cwd = _get_cwd()
            abs_path = os.path.join(cwd, filepath) if not os.path.isabs(filepath) else filepath
            content = v1_view_symbol(abs_path, symbol)
            return content
        else:
            return {"error": "Invalid SymbolURI format. Expected 'filepath#symbol'"}
    except Exception as e:
        return {"error": str(e)}

def find_references(id: str, MaxResults: int, Cursor: str = "") -> GuardedList:
    try:
        symbol = id.split("#")[1] if "#" in id else id
        if ":" in symbol:
            symbol = symbol.split(":", 1)[1]
            
        cwd = _get_cwd()
        output = v1_search_code(symbol, False, cwd)
        lines = output.split('\n') if output else []
        matches = []
        for line in lines[:MaxResults]:
            parts = line.split(":", 2)
            if len(parts) >= 2:
                file_path = parts[0]
                matches.append({"node_uri": f"{file_path}#{symbol}", "new_content": ""})
                
        next_cursor = str(MaxResults) if len(lines) > MaxResults else None
        return {"results": matches, "next_cursor": next_cursor}
    except Exception as e:
        return {"error": str(e)}

def search_semantic(NaturalLanguageQuery: str, MaxResults: int, Cursor: str = "") -> GuardedList:
    cwd = _get_cwd()
    try:
        # v1_semantic_search returns List[Dict{"file_path", "relevance_score"}]
        results = v1_semantic_search(NaturalLanguageQuery, 0.0, cwd)
        matches = []
        for r in results[:MaxResults]:
            matches.append({"node_uri": r["file_path"], "new_content": ""}) # Mocking NodeTarget structure
        next_cursor = str(MaxResults) if len(results) > MaxResults else None
        return {"results": matches, "next_cursor": next_cursor}
    except DiscoveryError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}

def search_structural(ASTPattern: str) -> GuardedList:
    cwd = _get_cwd()
    try:
        output = v1_search_code(ASTPattern, True, cwd)
        lines = output.split('\n') if output else []
        matches = []
        for line in lines[:100]:
            parts = line.split(":", 2)
            if len(parts) >= 2:
                file_path = parts[0]
                matches.append({"node_uri": f"{file_path}", "new_content": ""})
        return {"results": matches, "next_cursor": None}
    except Exception as e:
        return {"error": str(e)}

def grep_workspace(RegexPattern: str, MaxResults: int, Cursor: str = "") -> GuardedList:
    if RegexPattern is None:
        return {"error": "Missing required parameter: RegexPattern"}
    cwd = _get_cwd()
    try:
        output = v1_search_code(RegexPattern, True, cwd)
        lines = output.split('\n') if output else []
        matches = []
        for line in lines[:MaxResults]:
            parts = line.split(":", 2)
            if len(parts) >= 2:
                file_path = parts[0]
                line_num = int(parts[1]) if parts[1].isdigit() else 0
                snippet = parts[2] if len(parts) > 2 else ""
                matches.append({"file_path": file_path, "line_number": line_num, "snippet": snippet})
        
        next_cursor = str(MaxResults) if len(lines) > MaxResults else None
        return {"results": matches, "next_cursor": next_cursor}
    except DiscoveryError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": str(e)}
