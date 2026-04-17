from __future__ import annotations

import re
from lsprotocol import types as lsp
from lark import Tree, Token

from parser.lint import _text_of


_TOPLEVEL_KEYWORDS = [
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
    "Include",
    "UserKeywords",
    "UserFunctions",
    "Ann",
]

_SIGNAL_DIR_KEYWORDS = ["In", "Out", "InOut", "Supply", "Pseudo"]

_SIGNAL_ATTR_KEYWORDS = [
    "Termination",
    "DefaultState",
    "Base",
    "Alignment",
    "ScanIn",
    "ScanOut",
    "DataBitCount",
]

_TERMINATION_KEYWORDS = [
    "TerminateHigh",
    "TerminateLow",
    "TerminateOff",
    "TerminateUnknown",
]

_PATTERN_STMT_KEYWORDS = [
    "V",
    "Vector",
    "C",
    "Condition",
    "W",
    "WaveformTable",
    "Loop",
    "MatchLoop",
    "Call",
    "Macro",
    "Shift",
    "Goto",
    "Stop",
    "BreakPoint",
    "IDDQ",
    "ScanChain",
]

_EVENT_KEYWORDS = [
    "ForceDown",
    "ForceUp",
    "ForceOff",
    "ForcePrior",
    "ForceUnknown",
    "CompareLow",
    "CompareHigh",
    "CompareUnknown",
    "CompareOff",
    "CompareValid",
    "ExpectHigh",
    "ExpectOff",
    "Marker",
    "LogicLow",
    "LogicHigh",
    "LogicZ",
    "Unknown",
]

_SPEC_KEYWORDS = ["Category", "Variable", "Min", "Typ", "Max", "Meas"]

_PB_KEYWORDS = [
    "SignalGroups",
    "MacroDefs",
    "Procedures",
    "ScanStructures",
    "Start",
    "Stop",
    "Termination",
    "PatList",
]

_PE_KEYWORDS = ["Category", "Selector", "Timing", "PatternBurst"]


def _find_context(tree: Tree, line: int, col: int) -> list[str]:
    if tree.data != "start":
        return []

    context: list[str] = []
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        start_line = _line_of(inner)
        end_line = _end_line_of(inner)
        if start_line <= line <= end_line:
            block_type = inner.data
            context.append(block_type)
            _find_inner_context(inner, line, context)
            break
    return context


def _find_inner_context(block: Tree, line: int, context: list[str]) -> None:
    for child in block.children:
        if not isinstance(child, Tree):
            continue
        start = _line_of(child)
        end = _end_line_of(child)
        if start <= line <= end:
            if child.data in (
                "waveform_table",
                "waveforms_block",
                "subwaveforms_block",
                "pattern_body",
                "vec_data_item",
                "wfc_single",
                "sig_simple",
                "sig_detailed",
                "sg_simple",
                "sg_detailed",
                "proc_def",
                "macro_def",
                "spec_entry",
                "spec_var_simple",
                "spec_var_multi",
                "patlist_block",
                "pb_item",
                "loop_stmt",
                "matchloop_stmt",
                "shift_stmt",
            ):
                context.append(child.data)
            _find_inner_context(child, line, context)
            break


def _line_of(node) -> int:
    if isinstance(node, Tree):
        meta = getattr(node, "meta", None)
        if meta and hasattr(meta, "line"):
            return meta.line
    return 0


def _end_line_of(node) -> int:
    if isinstance(node, Tree):
        meta = getattr(node, "meta", None)
        if meta and hasattr(meta, "end_line"):
            return meta.end_line
        if node.children:
            return _end_line_of(node.children[-1])
    return _line_of(node)


def _collect_names(tree: Tree, block_type: str) -> list[str]:
    names: list[str] = []
    if tree.data != "start":
        return names
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != block_type:
            continue
        for item in inner.children:
            if isinstance(item, Tree) and item.children:
                name = _text_of(item.children[0]).strip('"')
                if name and not name.startswith("'"):
                    names.append(name)
    return names


def _collect_block_names(tree: Tree, block_type: str) -> list[str]:
    names: list[str] = []
    if tree.data != "start":
        return names
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != block_type:
            continue
        if inner.children:
            name = _text_of(inner.children[0]).strip('"')
            if name:
                names.append(name)
    return names


def _collect_wft_names(tree: Tree) -> list[str]:
    names: list[str] = []
    if tree.data != "start":
        return names
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != "timing_block":
            continue
        for item in inner.children:
            if (
                isinstance(item, Tree)
                and item.data == "waveform_table"
                and item.children
            ):
                name = _text_of(item.children[0]).strip('"')
                if name:
                    names.append(name)
    return names


def get_completions(
    tree: Tree, text: str, line: int, col: int
) -> list[lsp.CompletionItem]:
    context = _find_context(tree, line + 1, col)
    items: list[lsp.CompletionItem] = []

    if not context:
        items.extend(_keyword_items(_TOPLEVEL_KEYWORDS, lsp.CompletionItemKind.Keyword))
        return items

    current = context[-1] if context else ""

    if current == "signals_block":
        items.extend(
            _keyword_items(_SIGNAL_DIR_KEYWORDS, lsp.CompletionItemKind.Keyword)
        )
        items.extend(
            _keyword_items(_SIGNAL_ATTR_KEYWORDS, lsp.CompletionItemKind.Property)
        )
    elif current == "signalgroups_block":
        items.extend(
            _name_items(
                _collect_names(tree, "signals_block"), lsp.CompletionItemKind.Variable
            )
        )
    elif current in ("timing_block", "waveform_table"):
        items.extend(
            _keyword_items(
                [
                    "WaveformTable",
                    "Period",
                    "InheritWaveformTable",
                    "Waveforms",
                    "SubWaveforms",
                ],
                lsp.CompletionItemKind.Keyword,
            )
        )
        items.extend(
            _name_items(_collect_wft_names(tree), lsp.CompletionItemKind.Reference)
        )
    elif current in ("waveforms_block", "wfc_single"):
        items.extend(_keyword_items(_EVENT_KEYWORDS, lsp.CompletionItemKind.Value))
        items.extend(
            _name_items(
                _collect_names(tree, "signals_block"), lsp.CompletionItemKind.Variable
            )
        )
    elif current in ("pattern_block", "pattern_body"):
        items.extend(
            _keyword_items(_PATTERN_STMT_KEYWORDS, lsp.CompletionItemKind.Keyword)
        )
        items.extend(
            _name_items(_collect_wft_names(tree), lsp.CompletionItemKind.Reference)
        )
    elif current == "loop_stmt":
        items.extend(
            _keyword_items(_PATTERN_STMT_KEYWORDS, lsp.CompletionItemKind.Keyword)
        )
    elif current in ("proc_def", "macro_def"):
        items.extend(
            _keyword_items(_PATTERN_STMT_KEYWORDS, lsp.CompletionItemKind.Keyword)
        )
    elif current == "patternburst_block":
        items.extend(_keyword_items(_PB_KEYWORDS, lsp.CompletionItemKind.Keyword))
    elif current == "patternexec_block":
        items.extend(_keyword_items(_PE_KEYWORDS, lsp.CompletionItemKind.Keyword))
    elif current == "spec_block":
        items.extend(_keyword_items(_SPEC_KEYWORDS, lsp.CompletionItemKind.Keyword))
    else:
        items.extend(_keyword_items(_TOPLEVEL_KEYWORDS, lsp.CompletionItemKind.Keyword))

    if current in ("vec_data_item", "pattern_body", "pattern_block"):
        items.extend(
            _name_items(
                _collect_names(tree, "signalgroups_block"),
                lsp.CompletionItemKind.Variable,
            )
        )
        items.extend(
            _name_items(
                _collect_names(tree, "signals_block"), lsp.CompletionItemKind.Variable
            )
        )

    return items


def _keyword_items(
    keywords: list[str], kind: lsp.CompletionItemKind
) -> list[lsp.CompletionItem]:
    return [
        lsp.CompletionItem(label=kw, kind=kind, detail="STIL keyword")
        for kw in keywords
    ]


def _name_items(
    names: list[str], kind: lsp.CompletionItemKind
) -> list[lsp.CompletionItem]:
    seen = set()
    items = []
    for name in names:
        if name not in seen:
            seen.add(name)
            items.append(lsp.CompletionItem(label=name, kind=kind))
    return items
