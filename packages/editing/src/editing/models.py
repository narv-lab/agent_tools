from dataclasses import dataclass
from typing import List, Optional, Union, Literal

@dataclass
class ParseError:
    position: str
    reason: str

@dataclass
class SearchReplaceTarget:
    old_text: str
    new_text: str
    fuzzy_match: bool

@dataclass
class SymbolTarget:
    uri: str
    replacement: str

@dataclass
class AppendTarget:
    uri: str
    replacement: str

@dataclass
class UnifiedDiffTarget:
    diff_text: str

@dataclass
class ASTNodeTarget:
    node_uri: str
    new_content: str

EditTarget = Union[
    SearchReplaceTarget,
    SymbolTarget,
    AppendTarget,
    UnifiedDiffTarget,
    ASTNodeTarget
]

@dataclass
class Patch:
    target: EditTarget

@dataclass
class FilePatch:
    file_path: str
    intent: str
    patches: List[Patch]

@dataclass
class Diagnostic:
    level: Literal["Error", "Warn"]
    message: str
    uri: str
    file_revision: str

@dataclass
class ValidationResult:
    # is_valid: True iff AST validation succeeds and no new syntax errors are added (no degradation).
    # Even during text fallback (fallback_applied=True), it is True if application succeeds and errors do not increase.
    # L1 Design Principle: Existing errors are allowed, but adding new errors (degradation) makes it False.
    is_valid: bool
    # fallback_applied: True if text fallback was applied and AST validation was skipped or partially applied
    # (CHANGE-global-20260815-102100)
    fallback_applied: bool
    revision_checked: str
    # syntax_errors: Always returns the actual syntax parsing errors (does not swallow them).
    # Stores errors even if fallback_applied=True (CHANGE-global-20260815-103600)
    syntax_errors: List[ParseError]
    semantic_diagnostics: Union[List[str], List[Diagnostic]]

@dataclass
class PatchResult:
    success: bool
    applied_target: EditTarget
    error_reason: Optional[str]

@dataclass
class ApplyResult:
    overall_success: bool
    results: List[PatchResult]
    validation: Optional[ValidationResult]
