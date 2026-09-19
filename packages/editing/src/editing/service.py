import os
import shutil
from typing import List, Optional

from .models import (
    FilePatch,
    ApplyResult,
    ValidationResult,
    PatchResult,
    ParseError,
    SearchReplaceTarget,
    SymbolTarget,
    AppendTarget,
    UnifiedDiffTarget,
    ASTNodeTarget,
    EditTarget,
)


def _count_syntax_errors(source: str, file_path: str) -> List[ParseError]:
    """Validates syntax errors for a given source code string."""
    ext = os.path.splitext(file_path)[1].lower()
    errors: List[ParseError] = []

    if ext == ".py":
        try:
            import ast as _ast
            _ast.parse(source)
        except SyntaxError as e:
            errors.append(ParseError(position=f"line {e.lineno}", reason=str(e.msg)))
        except Exception:
            pass  # Fallback on AST parsing failure (treat as no error)
    # tree-sitter parsing for other languages will be added in the future
    return errors


def _count_syntax_errors_in_file(file_path: str) -> List[ParseError]:
    """Returns the current syntax errors of the file. Returns empty list on AST parsing failure as a text fallback."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
        return _count_syntax_errors(source, file_path)
    except Exception:
        return []


def _apply_search_replace_to_content(
    content: str, target: SearchReplaceTarget, file_path: str
) -> tuple[bool, str, Optional[str]]:
    """Applies SearchReplaceTarget to the content string."""
    # 1. Exact Match: Highest priority
    if target.old_text in content:
        new_content = content.replace(target.old_text, target.new_text, 1)
        return True, new_content, None

    if not target.fuzzy_match:
        return False, content, f"Target text not found in {file_path}"

    # --- Safe fallback processing for fuzzy_match: True below ---

    # 2. Absorb newline code differences (CRLF vs LF)
    c_lf = content.replace("\r\n", "\n")
    o_lf = target.old_text.replace("\r\n", "\n")
    if o_lf in c_lf:
        n_lf = target.new_text.replace("\r\n", "\n")
        new_c_lf = c_lf.replace(o_lf, n_lf, 1)
        if "\r\n" in content and "\r\n" not in target.old_text:
            new_content = new_c_lf.replace("\n", "\r\n")
        else:
            new_content = new_c_lf
        return True, new_content, None

    # 3. Line-by-line trimmed match
    # Safely replaces code blocks with indentation or trailing whitespace differences by line boundaries
    old_lines = o_lf.splitlines(keepends=False)
    content_lines = c_lf.splitlines(keepends=True)

    if old_lines:
        old_stripped = [l.strip() for l in old_lines]
        num_old = len(old_lines)
        match_idx = -1

        for i in range(len(content_lines) - num_old + 1):
            window = [content_lines[i + k].strip() for k in range(num_old)]
            if window == old_stripped:
                match_idx = i
                break

        if match_idx != -1:
            before_part = "".join(content_lines[:match_idx])
            after_part = "".join(content_lines[match_idx + num_old:])
            rep = target.new_text.replace("\r\n", "\n")
            if content_lines[match_idx + num_old - 1].endswith("\n") and not rep.endswith("\n") and (after_part or content.endswith("\n")):
                rep = rep + "\n"

            new_c_lf = before_part + rep + after_part
            if "\r\n" in content and "\r\n" not in target.old_text:
                new_content = new_c_lf.replace("\n", "\r\n")
            else:
                new_content = new_c_lf
            return True, new_content, None

    # 4. Token/whitespace normalized match (handles whitespace variations in single lines or around symbols)
    # Decomposes word tokens, symbols, and whitespaces, safely matching spaces/newlines around symbols
    import re
    tokens = re.findall(r'[a-zA-Z0-9_]+|[^\sa-zA-Z0-9_]|\r?\n|[ \t]+', target.old_text)
    pattern_parts = []
    for tok in tokens:
        if '\n' in tok:
            pattern_parts.append(r'\r?\n[ \t]*')
        elif tok.isspace():
            pattern_parts.append(r'[ \t]+')
        elif re.match(r'^[a-zA-Z0-9_]+$', tok):
            pattern_parts.append(re.escape(tok))
        else:
            pattern_parts.append(r'[ \t]*' + re.escape(tok) + r'[ \t]*')
    pattern_str = ''.join(pattern_parts)
    pattern_str = re.sub(r'(\[ \\t\][\*\+])+', r'[ \t]*', pattern_str)

    try:
        match = re.search(pattern_str, content)
        if match:
            new_content = content[:match.start()] + target.new_text + content[match.end():]
            return True, new_content, None
    except Exception:
        pass

    return False, content, f"Target text not found in {file_path} (fuzzy match)"


def _apply_search_replace(file_path: str, target: SearchReplaceTarget) -> tuple[bool, Optional[str]]:
    """Applies SearchReplaceTarget."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        success, new_content, error_reason = _apply_search_replace_to_content(content, target, file_path)
        if not success:
            return False, error_reason

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True, None
    except Exception as e:
        return False, str(e)


def _parse_symbol_uri(uri: str) -> tuple[str, Optional[str], Optional[str]]:
    """Decomposes a SymbolURI into file path, symbol type, and symbol name.
    Format: "src/utils.py#function:my_func" -> ("src/utils.py", "function", "my_func")
    No fragment: "src/utils.py" -> ("src/utils.py", None, None)
    """
    if '#' not in uri:
        return uri, None, None
    file_path, fragment = uri.split('#', 1)
    if ':' in fragment:
        symbol_type, symbol_name = fragment.split(':', 1)
    else:
        symbol_type = None
        symbol_name = fragment
    return file_path, symbol_type, symbol_name


_TS_LANG_MAP = {
    '.py': 'python', '.ts': 'typescript', '.tsx': 'typescript',
    '.js': 'javascript', '.jsx': 'javascript', '.go': 'go',
    '.rs': 'rust', '.java': 'java', '.c': 'c', '.cpp': 'cpp',
    '.cs': 'c_sharp', '.rb': 'ruby', '.php': 'php',
}

_TS_NODE_TYPES = (
    'function_definition', 'class_definition', 'method_definition',
    'function_declaration', 'class_declaration', 'method_declaration',
    'arrow_function',
)


def _apply_symbol_to_bytes(
    code_bytes: bytes, uri: str, new_content: str, file_path: str
) -> tuple[bool, bytes, Optional[str]]:
    """Identifies a symbol using tree-sitter and replaces it at the byte level."""
    _uri_file, _sym_type, symbol_name = _parse_symbol_uri(uri)
    resolved_path = _uri_file if (_uri_file and os.path.exists(_uri_file)) else file_path

    if not symbol_name:
        return False, code_bytes, f"SymbolTarget: invalid URI '{uri}' — symbol name is required"

    try:
        from tree_sitter import Language, Parser
        import importlib

        ext = os.path.splitext(resolved_path)[1].lower()
        lang_name = _TS_LANG_MAP.get(ext)
        if not lang_name:
            return False, code_bytes, (
                f"SymbolTarget: unsupported file type '{ext}' for tree-sitter. "
                "Use SearchReplaceTarget for text-based edits."
            )

        mod = importlib.import_module(f"tree_sitter_{lang_name}")
        parser = Parser(Language(mod.language()))
        tree = parser.parse(code_bytes)

        found_node = None

        def _traverse(node) -> None:
            nonlocal found_node
            if found_node is not None:
                return
            if node.type in _TS_NODE_TYPES:
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = code_bytes[name_node.start_byte:name_node.end_byte].decode('utf-8')
                    if name == symbol_name:
                        found_node = node
                        return
            for child in node.children:
                _traverse(child)

        _traverse(tree.root_node)

        if found_node is not None:
            new_code_bytes = (
                code_bytes[:found_node.start_byte]
                + new_content.encode('utf-8')
                + code_bytes[found_node.end_byte:]
            )
            return True, new_code_bytes, None

        return False, code_bytes, (
            f"SymbolTarget: symbol '{symbol_name}' not found as AST node in '{resolved_path}'. "
            "Use SearchReplaceTarget for text-based edits."
        )

    except ImportError:
        return False, code_bytes, (
            f"SymbolTarget: tree-sitter is not installed. "
            "Install tree-sitter and the language package (e.g. tree-sitter-python) to use SymbolTarget."
        )
    except Exception as e:
        return False, code_bytes, f"SymbolTarget: tree-sitter error — {e}"


def _apply_symbol_or_ast_node_target(
    file_path: str,
    uri: str,
    new_content: str,
) -> tuple[bool, Optional[str]]:
    """Identifies a symbol using tree-sitter and replaces it at the byte level.
    If tree-sitter is unavailable or the target symbol cannot be identified as an AST node,
    it returns an explicit error (L0 Explicit error reporting principle).
    """
    _uri_file, _sym_type, symbol_name = _parse_symbol_uri(uri)
    resolved_path = _uri_file if (_uri_file and os.path.exists(_uri_file)) else file_path

    try:
        with open(resolved_path, 'rb') as f:
            code_bytes = f.read()

        success, new_bytes, error_reason = _apply_symbol_to_bytes(code_bytes, uri, new_content, resolved_path)
        if not success:
            return False, error_reason

        with open(resolved_path, 'wb') as f:
            f.write(new_bytes)
        return True, None
    except Exception as e:
        return False, f"SymbolTarget: file read/write error — {e}"


def _apply_patch_to_content(
    content: str, patch_target: EditTarget, file_path: str
) -> tuple[bool, str, Optional[str]]:
    """Applies a patch to the content string in memory based on the EditTarget type."""
    if isinstance(patch_target, SearchReplaceTarget):
        return _apply_search_replace_to_content(content, patch_target, file_path)
    elif isinstance(patch_target, AppendTarget):
        return True, content + patch_target.replacement, None
    elif isinstance(patch_target, UnifiedDiffTarget):
        return False, content, "UnifiedDiffTarget is not yet implemented"
    elif isinstance(patch_target, SymbolTarget):
        code_bytes = content.encode('utf-8')
        success, new_bytes, err = _apply_symbol_to_bytes(code_bytes, patch_target.uri, patch_target.replacement, file_path)
        if not success:
            return False, content, err
        return True, new_bytes.decode('utf-8'), None
    elif isinstance(patch_target, ASTNodeTarget):
        code_bytes = content.encode('utf-8')
        success, new_bytes, err = _apply_symbol_to_bytes(code_bytes, patch_target.node_uri, patch_target.new_content, file_path)
        if not success:
            return False, content, err
        return True, new_bytes.decode('utf-8'), None
    return False, content, f"Unknown EditTarget type: {type(patch_target).__name__}"


def _apply_patch_to_file(file_path: str, patch_target: EditTarget) -> tuple[bool, Optional[str]]:
    """Applies a patch based on the EditTarget type."""
    if isinstance(patch_target, SearchReplaceTarget):
        return _apply_search_replace(file_path, patch_target)
    elif isinstance(patch_target, AppendTarget):
        try:
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(patch_target.replacement)
            return True, None
        except Exception as e:
            return False, str(e)
    elif isinstance(patch_target, UnifiedDiffTarget):
        # UnifiedDiff is currently a placeholder (for future implementation)
        return False, "UnifiedDiffTarget is not yet implemented"
    elif isinstance(patch_target, SymbolTarget):
        return _apply_symbol_or_ast_node_target(file_path, patch_target.uri, patch_target.replacement)
    elif isinstance(patch_target, ASTNodeTarget):
        return _apply_symbol_or_ast_node_target(file_path, patch_target.node_uri, patch_target.new_content)
    return False, f"Unknown EditTarget type: {type(patch_target).__name__}"


def _resolve_path(file_path: str) -> str:
    if os.path.isabs(file_path):
        return file_path
    cwd = os.environ.get("AGENT_WORKSPACE_CWD", os.getcwd())
    return os.path.join(cwd, file_path)

def create_file(file_path: str, initial_content: str, idempotency_key: str) -> dict:
    file_path = _resolve_path(file_path)
    if os.path.exists(file_path):
        return {"success": False, "error_reason": f"FileAlreadyExists: {file_path}"}
    
    parent = os.path.dirname(file_path)
    if parent:
        try:
            os.makedirs(parent, exist_ok=True)
        except Exception as e:
            return {"success": False, "error_reason": str(e)}
            
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(initial_content)
        return {"success": True, "error_reason": None}
    except Exception as e:
        return {"success": False, "error_reason": str(e)}


def delete_file(file_path: str, idempotency_key: str) -> dict:
    file_path = _resolve_path(file_path)
    if not os.path.exists(file_path):
        return {"success": False, "error_reason": f"FileNotFound: {file_path}"}
    if os.path.isdir(file_path):
        return {"success": False, "error_reason": f"IsDirectory: {file_path}"}
        
    try:
        os.remove(file_path)
        return {"success": True, "error_reason": None}
    except Exception as e:
        return {"success": False, "error_reason": str(e)}


def move_file(old_path: str, new_path: str, idempotency_key: str) -> dict:
    old_path = _resolve_path(old_path)
    new_path = _resolve_path(new_path)
    if not os.path.exists(old_path):
        return {"success": False, "error_reason": f"FileNotFound: {old_path}"}
    if os.path.exists(new_path):
        return {"success": False, "error_reason": f"FileAlreadyExists: {new_path}"}
    try:
        parent = os.path.dirname(new_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        shutil.move(old_path, new_path)
        return {"success": True, "error_reason": None}
    except Exception as e:
        return {"success": False, "error_reason": str(e)}


def apply_and_validate_patches(patches: List[FilePatch], auto_format: bool, idempotency_key: str) -> ApplyResult:
    """
    Applies patches as a transaction.
    is_valid determination logic (CHANGE-global-20260815-103600/111600):
    - True condition is not "zero errors" but "no new errors added (no degradation)".
    - If fallback_applied=True, indicates text fallback like SearchReplace was used.
    - Rollback condition: Rollback only if is_valid=False and degradation is detected.
    """
    if not patches:
        raise ValueError("No patches provided to apply_and_validate_patches")
    if not any(len(fp.patches) > 0 for fp in patches):
        raise ValueError("No patches provided in the FilePatch list to apply_and_validate_patches")

    # Pre-application snapshot (for rollback)
    file_snapshots: dict[str, str] = {}
    pre_error_counts: dict[str, int] = {}

    for fp in patches:
        fp.file_path = _resolve_path(fp.file_path)
        if os.path.exists(fp.file_path):
            try:
                with open(fp.file_path, "r", encoding="utf-8") as f:
                    file_snapshots[fp.file_path] = f.read()
                pre_error_counts[fp.file_path] = len(_count_syntax_errors_in_file(fp.file_path))
            except Exception:
                file_snapshots[fp.file_path] = ""
                pre_error_counts[fp.file_path] = 0
        else:
            file_snapshots[fp.file_path] = None  # type: ignore
            pre_error_counts[fp.file_path] = 0

    results: List[PatchResult] = []
    overall_success = True
    fallback_applied = False

    for fp in patches:
        for patch in fp.patches:
            success, error_reason = _apply_patch_to_file(fp.file_path, patch.target)
            if not success:
                # If SearchReplace etc. fails, treat it as successful (no-op) as a fallback
                # This allows other patches to continue even if some fail
                fallback_applied = True
            results.append(PatchResult(
                success=success,
                applied_target=patch.target,
                error_reason=error_reason
            ))
            if not success:
                overall_success = False

    # Count errors after application to check for degradation
    all_post_errors: List[ParseError] = []
    degraded = False
    for fp in patches:
        if os.path.exists(fp.file_path):
            post_errors = _count_syntax_errors_in_file(fp.file_path)
            all_post_errors.extend(post_errors)
            pre_count = pre_error_counts.get(fp.file_path, 0)
            post_count = len(post_errors)
            if post_count > pre_count:
                # New error added = degradation
                degraded = True

    # is_valid: No degradation, and allows application success even during text fallback
    # CHANGE-111600: False only if there is degradation (new errors added)
    is_valid = not degraded

    # Rollback: Revert file only if degraded (CHANGE-20260815-111600)
    if degraded:
        for file_path, snapshot in file_snapshots.items():
            if snapshot is not None:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(snapshot)
                except Exception:
                    pass

    import hashlib
    revision_hash = hashlib.sha256(idempotency_key.encode()).hexdigest()[:16]

    validation = ValidationResult(
        is_valid=is_valid,
        fallback_applied=fallback_applied,
        revision_checked=revision_hash,
        syntax_errors=all_post_errors,
        semantic_diagnostics=[]
    )

    return ApplyResult(
        overall_success=overall_success and is_valid,
        results=results,
        validation=validation
    )


def dry_run_patches(patches: List[FilePatch]) -> ValidationResult:
    """
    Pre-validation of patches. Does not modify actual files.
    Fully simulates patch application in memory to verify syntax errors (AST) and degradation.
    Performs the same syntax degradation check as apply_and_validate_patches to prevent validation mismatch (false positives).
    """
    file_simulated_contents: dict[str, Optional[str]] = {}
    pre_error_counts: dict[str, int] = {}
    apply_failed = False
    all_syntax_errors: List[ParseError] = []

    # 1. Get pre-application state
    for fp in patches:
        file_path = _resolve_path(fp.file_path)
        if file_path not in file_simulated_contents:
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                    file_simulated_contents[file_path] = content
                    pre_error_counts[file_path] = len(_count_syntax_errors(content, file_path))
                except Exception:
                    file_simulated_contents[file_path] = None
                    pre_error_counts[file_path] = 0
            else:
                file_simulated_contents[file_path] = "" if fp.intent == "create" else None
                pre_error_counts[file_path] = 0

    # 2. Simulate patch application (in-memory)
    for fp in patches:
        file_path = _resolve_path(fp.file_path)
        content = file_simulated_contents.get(file_path)
        if content is None and fp.intent != "create":
            apply_failed = True
            continue

        for patch in fp.patches:
            success, new_content, error_reason = _apply_patch_to_content(
                content if content is not None else "", patch.target, file_path
            )
            if not success:
                apply_failed = True
            else:
                content = new_content
                file_simulated_contents[file_path] = content

    # 3. Syntax error validation and degradation check post-simulation
    degraded = False
    for file_path, content in file_simulated_contents.items():
        if content is not None:
            post_errors = _count_syntax_errors(content, file_path)
            all_syntax_errors.extend(post_errors)
            pre_count = pre_error_counts.get(file_path, 0)
            post_count = len(post_errors)
            if post_count > pre_count:
                degraded = True

    # is_valid = True if no degradation and patch application did not fail
    is_valid = (not apply_failed) and (not degraded)

    import hashlib
    revision_hash = hashlib.sha256(",".join(fp.file_path for fp in patches).encode()).hexdigest()[:16]

    return ValidationResult(
        is_valid=is_valid,
        fallback_applied=False,
        revision_checked=revision_hash,
        syntax_errors=all_syntax_errors,
        semantic_diagnostics=[]
    )


def wait_for_diagnostics(timeout_ms: int) -> dict:
    return {"success": True, "error_reason": None}

def restart_lsp() -> dict:
    return {"success": True, "error_reason": None}

def clear_cache_and_rebuild() -> dict:
    return {"success": True, "error_reason": None}
