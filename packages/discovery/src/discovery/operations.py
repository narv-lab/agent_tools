import os
import glob

import math
import collections
import re
from typing import Optional, List, Dict
from pathlib import Path

from .exceptions import (
    DirectoryNotFoundError,
    PermissionDeniedError,
    InvalidPatternError,
    EmptyQueryError,
    IndexingFailedError,
    InvalidRegexError,
    TooManyMatchesError,
    FileNotFoundError,
    InvalidRangeError,
    SymbolNotFoundError,
    ParseError,
    CommandExecutionError,
    FileReadError
)

LANGUAGE_MAP = {
    # Programming languages (major languages with Tree-sitter parsers)
    '.py': 'python',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'tsx',
    '.java': 'java',
    '.go': 'go',
    '.rs': 'rust',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cs': 'c_sharp',
    '.rb': 'ruby',
    '.php': 'php',
    # Structured documents (PO exception: CHANGE-agent_tools_supported_languages-20260814-234500)
    '.json': 'json',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.md': 'markdown',
    '.markdown': 'markdown',
    '.html': 'html',
    '.htm': 'html',
    '.xml': 'xml',
    '.css': 'css',
    '.scss': 'scss',
}

_ts_parsers = {}

def _get_ts_parser(file_path: str):
    try:
        from tree_sitter import Language, Parser
    except ImportError:
        return None
        
    ext = os.path.splitext(file_path)[1].lower()
    lang_name = LANGUAGE_MAP.get(ext)
    if not lang_name:
        return None
        
    if lang_name in _ts_parsers:
        return _ts_parsers[lang_name]
        
    try:
        import importlib
        module = importlib.import_module(f"tree_sitter_{lang_name}")
        parser = Parser(Language(module.language()))
        _ts_parsers[lang_name] = parser
        return parser
    except Exception:
        _ts_parsers[lang_name] = None
        return None

def get_repo_map(target_dir: str, depth: int) -> str:
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise DirectoryNotFoundError(target_dir)
    if not os.access(target_dir, os.R_OK | os.X_OK):
        raise PermissionDeniedError(target_dir)
        
    if depth < 1:
        depth = 1
        
    result = []
    root_path = Path(target_dir)
    
    try:
        for p in root_path.rglob('*'):
            if p.is_file():
                rel_parts = p.relative_to(root_path).parts
                if len(rel_parts) > depth:
                    continue
                
                symbols_str = ""
                parser = _get_ts_parser(str(p))
                if parser:
                    try:
                        with open(p, 'rb') as f:
                            code = f.read()
                        tree = parser.parse(code)
                        symbols = []
                        
                        def traverse(node):
                            if node.type in (
                                'function_definition', 'class_definition', 'method_definition',
                                'function_declaration', 'class_declaration', 'method_declaration'
                            ):
                                name_node = node.child_by_field_name('name')
                                if name_node:
                                    symbols.append(code[name_node.start_byte:name_node.end_byte].decode('utf-8'))
                            for child in node.children:
                                traverse(child)
                                
                        traverse(tree.root_node)
                        if symbols:
                            symbols_str = " [" + ", ".join(symbols) + "]"
                    except Exception:
                        pass # Silently fallback to filename only as per L1
                
                result.append(f"{str(p.relative_to(root_path))}{symbols_str}")
    except PermissionError as e:
        raise PermissionDeniedError(str(e.filename) if e.filename else target_dir)
            
    return "\n".join(result)

def list_files(target_dir: str, pattern: str) -> List[str]:
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise DirectoryNotFoundError(target_dir)
    
    try:
        search_path = os.path.join(target_dir, pattern)
        matched = glob.glob(search_path, recursive=True)
    except Exception as e:
        raise InvalidPatternError(pattern, str(e))
        
    target_abs = os.path.abspath(target_dir)
    result = []
    for p in matched:
        if os.path.isfile(p):
            p_abs = os.path.abspath(p)
            if os.path.commonpath([target_abs, p_abs]) == target_abs:
                result.append(p_abs)
                
    return sorted(result)[:1000]

_index_cache = {
    'dir': None,
    'mtimes': {},
    'docs': {},
    'tf': {},
    'df': collections.Counter(),
    'doc_len': {},
    'avgdl': 0.0,
    'N': 0
}

def _tokenize(text: str) -> List[str]:
    return re.findall(r'[a-zA-Z0-9_]+', text.lower())

def _build_or_update_index(target_dir: str):
    global _index_cache
    if _index_cache['dir'] != target_dir:
        _index_cache = {
            'dir': target_dir,
            'mtimes': {},
            'docs': {},
            'tf': {},
            'df': collections.Counter(),
            'doc_len': {},
            'avgdl': 0.0,
            'N': 0
        }
    
    current_files = set()
    for root, dirs, files in os.walk(target_dir):
        if '.git' in dirs:
            dirs.remove('.git')
        if '__pycache__' in dirs:
            dirs.remove('__pycache__')
            
        for f in files:
            if f.startswith('.'):
                continue
            if f.endswith(('.pyc', '.png', '.jpg', '.jpeg', '.pdf', '.zip', '.tar', '.gz', '.mp4', '.mp3')):
                continue
                
            file_path = os.path.join(root, f)
            current_files.add(file_path)
            
            try:
                mtime = os.path.getmtime(file_path)
            except OSError:
                continue
                
            if file_path not in _index_cache['mtimes'] or _index_cache['mtimes'][file_path] != mtime:
                try:
                    with open(file_path, 'r', encoding='utf-8') as fh:
                        content = fh.read()
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue
                
                tokens = _tokenize(content)
                tf = collections.Counter(tokens)
                
                if file_path in _index_cache['tf']:
                    old_tf = _index_cache['tf'][file_path]
                    for t in old_tf.keys():
                        _index_cache['df'][t] -= 1
                
                _index_cache['tf'][file_path] = tf
                _index_cache['doc_len'][file_path] = len(tokens)
                _index_cache['mtimes'][file_path] = mtime
                for t in tf.keys():
                    _index_cache['df'][t] += 1

    deleted_files = set(_index_cache['mtimes'].keys()) - current_files
    for file_path in deleted_files:
        old_tf = _index_cache['tf'][file_path]
        for t in old_tf.keys():
            _index_cache['df'][t] -= 1
        del _index_cache['tf'][file_path]
        del _index_cache['doc_len'][file_path]
        del _index_cache['mtimes'][file_path]
        
    _index_cache['N'] = len(_index_cache['mtimes'])
    if _index_cache['N'] > 0:
        _index_cache['avgdl'] = sum(_index_cache['doc_len'].values()) / _index_cache['N']
    else:
        _index_cache['avgdl'] = 0.0

def semantic_search(query: str, score_threshold: float = 0.0, target_dir: Optional[str] = None) -> List[Dict]:
    if not query.strip():
        raise EmptyQueryError()
        
    search_dir = target_dir if target_dir else os.getcwd()
    if not os.path.exists(search_dir):
        raise DirectoryNotFoundError(search_dir)
        
    try:
        _build_or_update_index(search_dir)
    except Exception as e:
        raise IndexingFailedError(str(e))
        
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
        
    k1 = 1.5
    b = 0.75
    
    results = []
    N = _index_cache['N']
    avgdl = _index_cache['avgdl']
    
    max_possible_score = 0.0
    for q in query_tokens:
        n_q = _index_cache['df'].get(q, 0)
        idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
        max_possible_score += idf * (k1 + 1)
        
    for file_path, tf in _index_cache['tf'].items():
        score = 0.0
        doc_len = _index_cache['doc_len'][file_path]
        for q in query_tokens:
            if q not in tf:
                continue
            
            n_q = _index_cache['df'].get(q, 0)
            idf = math.log((N - n_q + 0.5) / (n_q + 0.5) + 1.0)
            
            f_q = tf[q]
            num = f_q * (k1 + 1)
            den = f_q + k1 * (1 - b + b * (doc_len / avgdl)) if avgdl > 0 else f_q + k1
            
            score += idf * (num / den)
            
        if max_possible_score > 0:
            score = score / max_possible_score
            
        if score >= score_threshold:
            results.append({
                "file_path": os.path.abspath(file_path),
                "relevance_score": score
            })
            
    results.sort(key=lambda x: x["relevance_score"], reverse=True)
    return results[:1000]

def search_code(query: str, is_regex: bool, target_dir: str) -> str:
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        raise DirectoryNotFoundError(target_dir)
        
    cmd = ["rg", "-n", "--no-heading", "--color=never"]
    if not is_regex:
        cmd.append("-F")
    cmd.extend(["-e", query, "."])
    
    cmd_str = f"cd {target_dir} && " + " ".join([f'"{c}"' if " " in c else c for c in cmd])
    
    try:
        from execution.service import ExecutionService
        exec_svc = ExecutionService()
        result = exec_svc.execute_bash(cmd_str, timeout_ms=30000, profile=None, overrides={})

        # FINDING-003: execute_bash might return Error union (L2 execution_v2 v2.1.0)
        if isinstance(result, dict) and "error" in result:
            raise CommandExecutionError(f"execute_bash failed: {result['error']}")

        if result.exit_code == 2:
            raise InvalidRegexError(query, "rg returned error code 2 (invalid regex)")
        
        output = result.stdout.strip()
        if not output:
            return ""

            
        lines = output.split('\n')
        limit = 1000
        if len(lines) > limit:
            raise TooManyMatchesError(len(lines), limit)
            
        return output
    except Exception as e:
        if isinstance(e, (DirectoryNotFoundError, InvalidRegexError, TooManyMatchesError)):
            raise
        raise CommandExecutionError(f"Command execution failed: {e}")

def view_file(file_path: str, start_line: Optional[int] = None, end_line: Optional[int] = None) -> str:
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
        
    if start_line is not None and start_line < 1:
        raise InvalidRangeError("start_line must be >= 1")
    if start_line is not None and end_line is not None and start_line > end_line:
        raise InvalidRangeError("start_line > end_line")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except PermissionError:
        raise PermissionDeniedError(file_path)
    except Exception as e:
        raise FileReadError(file_path, str(e))
        
    start = (start_line - 1) if start_line is not None else 0
    end = end_line if end_line is not None else len(lines)
    
    MAX_LINES = 1000
    if end - start > MAX_LINES:
        end = start + MAX_LINES
    
    result = []
    for i in range(start, min(end, len(lines))):
        result.append(f"{i + 1}: {lines[i].rstrip('\\n')}")
        
    return "\n".join(result)

def view_symbol(file_path: str, symbol_name: str) -> str:
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        raise FileNotFoundError(file_path)
        
    parser = _get_ts_parser(file_path)
    if not parser:
        raise ParseError(file_path, "Tree-sitter parser not available or language not supported")

    try:
        with open(file_path, 'rb') as f:
            code = f.read()
        tree = parser.parse(code)
    except Exception as e:
        raise ParseError(file_path, f"Parse error: {e}")
        
    matched_nodes = []
    
    def traverse(node):
        if node.type in (
            'function_definition', 'class_definition', 'method_definition',
            'function_declaration', 'class_declaration', 'method_declaration'
        ):
            name_node = node.child_by_field_name('name')
            if name_node:
                name = code[name_node.start_byte:name_node.end_byte].decode('utf-8')
                if name == symbol_name:
                    matched_nodes.append(node)
        for child in node.children:
            traverse(child)
            
    traverse(tree.root_node)
    
    if not matched_nodes:
        raise SymbolNotFoundError(symbol_name, file_path)
        
    code_str = code.decode('utf-8')
    lines = code_str.split('\n')
    
    result = []
    for node in matched_nodes:
        start_row = node.start_point[0]
        end_row = node.end_point[0]
        for i in range(start_row, end_row + 1):
            if i < len(lines):
                result.append(f"{i + 1}: {lines[i]}")
        result.append("---")
        
    if result and result[-1] == "---":
        result.pop()
        
    return "\n".join(result)
