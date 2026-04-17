from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from lark import Tree, Token


class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Diagnostic:
    line: int
    column: int
    severity: Severity
    message: str

    def __str__(self):
        return f"[{self.line}:{self.column}] {self.severity.value}: {self.message}"


@dataclass
class LintResult:
    diagnostics: list[Diagnostic] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(d.severity == Severity.ERROR for d in self.diagnostics)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == Severity.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.severity == Severity.WARNING]


REQUIRED_ORDER = [
    "STIL",
    "Header",
    "Signals",
    "SignalGroups",
    "ScanStructures",
    "Spec",
    "Timing",
    "Selector",
    "PatternBurst",
    "PatternExec",
    "Procedures",
    "MacroDefs",
    "Pattern",
]

ORDER_INDEX = {name: i for i, name in enumerate(REQUIRED_ORDER)}


def _block_type(tree: Tree) -> Optional[str]:
    mapping = {
        "header_block": "Header",
        "signals_block": "Signals",
        "signalgroups_block": "SignalGroups",
        "scanstructures_block": "ScanStructures",
        "spec_block": "Spec",
        "selector_block": "Selector",
        "timing_block": "Timing",
        "patternburst_block": "PatternBurst",
        "patternexec_block": "PatternExec",
        "procedures_block": "Procedures",
        "macrodefs_block": "MacroDefs",
        "pattern_block": "Pattern",
    }
    return mapping.get(tree.data)


def _line(tree: Tree) -> int:
    return getattr(tree, "meta", None) and getattr(tree.meta, "line", 0) or 0


def _text_of(tok_or_tree) -> str:
    if isinstance(tok_or_tree, Token):
        return str(tok_or_tree)
    if isinstance(tok_or_tree, Tree):
        children = tok_or_tree.children
        if children:
            return _text_of(children[0])
    return ""


def lint(tree: Tree, path: str = "<input>") -> LintResult:
    result = LintResult()

    if tree.data != "start":
        return result

    _check_block_ordering(tree, result)
    _check_duplicate_signals(tree, result)
    _check_duplicate_signalgroups(tree, result)
    _check_duplicate_patterns(tree, result)
    _check_wfc_uniqueness(tree, result)

    return result


def _check_block_ordering(start: Tree, result: LintResult) -> None:
    last_idx = -1
    last_block = ""
    for child in start.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        btype = _block_type(inner)
        if btype is None:
            continue
        idx = ORDER_INDEX.get(btype, -1)
        if idx < 0:
            continue
        if idx < last_idx:
            result.diagnostics.append(
                Diagnostic(
                    line=_line(inner),
                    column=0,
                    severity=Severity.WARNING,
                    message=f"{btype} block appears after {last_block}, violating recommended ordering (IEEE 1450 Table 7)",
                )
            )
        last_idx = idx
        last_block = btype


def _collect_item_names(block_type: str, start: Tree) -> list[tuple[str, int]]:
    names: list[tuple[str, int]] = []
    for child in start.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != block_type:
            continue
        for item in inner.children:
            if isinstance(item, Tree) and item.children:
                name = _text_of(item.children[0]).strip('"')
                names.append((name, _line(item)))
    return names


def _collect_block_names(block_type: str, start: Tree) -> list[tuple[str, int]]:
    names: list[tuple[str, int]] = []
    for child in start.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != block_type:
            continue
        if inner.children:
            name = _text_of(inner.children[0]).strip('"')
            names.append((name, _line(inner)))
    return names


def _check_duplicate_names(
    entries: list[tuple[str, int]],
    kind: str,
    result: LintResult,
    severity: Severity = Severity.ERROR,
) -> None:
    seen: dict[str, int] = {}
    for name, line in entries:
        if name in seen:
            result.diagnostics.append(
                Diagnostic(
                    line=line,
                    column=0,
                    severity=severity,
                    message=f"Duplicate {kind} '{name}' (first defined at line {seen[name]})",
                )
            )
        else:
            seen[name] = line


def _check_duplicate_signals(start: Tree, result: LintResult) -> None:
    _check_duplicate_names(
        _collect_item_names("signals_block", start), "signal name", result
    )


def _check_duplicate_signalgroups(start: Tree, result: LintResult) -> None:
    _check_duplicate_names(
        _collect_item_names("signalgroups_block", start), "signal group name", result
    )


def _check_duplicate_patterns(start: Tree, result: LintResult) -> None:
    _check_duplicate_names(
        _collect_block_names("pattern_block", start), "pattern name", result
    )


def _check_wfc_uniqueness(start: Tree, result: LintResult) -> None:
    for child in start.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data == "timing_block":
            _check_wfc_in_timing(inner, result)


def _check_wfc_in_timing(timing: Tree, result: LintResult) -> None:
    for item in timing.children:
        if not isinstance(item, Tree):
            continue
        if item.data == "timing_item":
            for sub in item.children:
                if isinstance(sub, Tree) and sub.data == "waveform_table":
                    _check_wfc_in_wft(sub, result)
        elif item.data == "waveform_table":
            _check_wfc_in_wft(item, result)


def _check_wfc_in_wft(wft: Tree, result: LintResult) -> None:
    for item in wft.children:
        if not isinstance(item, Tree):
            continue
        if item.data == "wft_item":
            for sub in item.children:
                if isinstance(sub, Tree) and sub.data == "waveforms_block":
                    _check_wfc_in_waveforms(sub, result)
        elif item.data == "waveforms_block":
            _check_wfc_in_waveforms(item, result)


def _check_wfc_in_waveforms(waveforms: Tree, result: LintResult) -> None:
    for entry in waveforms.children:
        if not isinstance(entry, Tree) or entry.data != "waveform_entry":
            continue
        sig_name = _text_of(entry.children[0]) if entry.children else "<unknown>"
        seen_wfcs: dict[str, int] = {}
        for wfc_def in entry.children:
            if not isinstance(wfc_def, Tree):
                continue
            if wfc_def.data in ("wfc_single", "wfc_list_block", "wfc_subwf_block"):
                wfc_token = wfc_def.children[0] if wfc_def.children else None
                if wfc_token is not None:
                    wfc_str = str(wfc_token)
                    line = _line(wfc_def)
                    if wfc_str in seen_wfcs:
                        result.diagnostics.append(
                            Diagnostic(
                                line=line,
                                column=0,
                                severity=Severity.ERROR,
                                message=f"Duplicate WFC '{wfc_str}' for signal/group '{sig_name}' (first defined at line {seen_wfcs[wfc_str]})",
                            )
                        )
                    else:
                        seen_wfcs[wfc_str] = line
