from __future__ import annotations

from lsprotocol import types as lsp
from lark import Tree, Token

from parser.lint import _text_of


BLOCK_KINDS = {
    "header_block": lsp.SymbolKind.Class,
    "signals_block": lsp.SymbolKind.Class,
    "signalgroups_block": lsp.SymbolKind.Class,
    "scanstructures_block": lsp.SymbolKind.Class,
    "spec_block": lsp.SymbolKind.Class,
    "selector_block": lsp.SymbolKind.Class,
    "timing_block": lsp.SymbolKind.Class,
    "patternburst_block": lsp.SymbolKind.Class,
    "patternexec_block": lsp.SymbolKind.Class,
    "procedures_block": lsp.SymbolKind.Class,
    "macrodefs_block": lsp.SymbolKind.Class,
    "pattern_block": lsp.SymbolKind.Class,
}

BLOCK_LABELS = {
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


def _line_of(node) -> int:
    if isinstance(node, Tree):
        meta = getattr(node, "meta", None)
        if meta and hasattr(meta, "line"):
            return max(meta.line - 1, 0)
    return 0


def _end_line_of(node) -> int:
    if isinstance(node, Tree):
        meta = getattr(node, "meta", None)
        if meta and hasattr(meta, "end_line"):
            return max(meta.end_line - 1, 0)
        children = node.children
        if children:
            return _end_line_of(children[-1])
    return _line_of(node)


def _range_for(node) -> lsp.Range:
    start = lsp.Position(line=_line_of(node), character=0)
    end = lsp.Position(line=_end_line_of(node), character=0)
    return lsp.Range(start=start, end=end)


def _name_of_block(block: Tree) -> str | None:
    if not block.children:
        return None
    first = block.children[0]
    if isinstance(first, (Tree, Token)):
        return _text_of(first).strip('"')
    return None


def collect_symbols(tree: Tree) -> list[lsp.DocumentSymbol]:
    if tree.data != "start":
        return []

    symbols: list[lsp.DocumentSymbol] = []
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data == "signals_block":
            symbols.append(_signals_symbol(inner))
        elif inner.data == "signalgroups_block":
            symbols.append(_signalgroups_symbol(inner))
        elif inner.data == "timing_block":
            symbols.append(_timing_symbol(inner))
        elif inner.data == "pattern_block":
            symbols.append(_named_block_symbol(inner, "Pattern"))
        elif inner.data == "patternburst_block":
            symbols.append(_named_block_symbol(inner, "PatternBurst"))
        elif inner.data == "procedures_block":
            symbols.append(_named_block_symbol(inner, "Procedures"))
        elif inner.data == "macrodefs_block":
            symbols.append(_named_block_symbol(inner, "MacroDefs"))
        elif inner.data == "spec_block":
            symbols.append(_named_block_symbol(inner, "Spec"))
        elif inner.data == "selector_block":
            symbols.append(_named_block_symbol(inner, "Selector"))
        elif inner.data == "scanstructures_block":
            symbols.append(_named_block_symbol(inner, "ScanStructures"))
        elif inner.data == "patternexec_block":
            symbols.append(_named_block_symbol(inner, "PatternExec"))
        elif inner.data == "header_block":
            symbols.append(
                lsp.DocumentSymbol(
                    name="Header",
                    kind=lsp.SymbolKind.Class,
                    range=_range_for(inner),
                    selection_range=_range_for(inner),
                )
            )
    return symbols


def _signals_symbol(block: Tree) -> lsp.DocumentSymbol:
    children = []
    for item in block.children:
        if isinstance(item, Tree) and item.children:
            name = _text_of(item.children[0]).strip('"')
            children.append(
                lsp.DocumentSymbol(
                    name=name,
                    kind=lsp.SymbolKind.Variable,
                    range=_range_for(item),
                    selection_range=_range_for(item),
                )
            )
    return lsp.DocumentSymbol(
        name="Signals",
        kind=lsp.SymbolKind.Class,
        range=_range_for(block),
        selection_range=_range_for(block),
        children=children,
    )


def _signalgroups_symbol(block: Tree) -> lsp.DocumentSymbol:
    children = []
    for item in block.children:
        if isinstance(item, Tree) and item.children:
            name = _text_of(item.children[0]).strip('"')
            children.append(
                lsp.DocumentSymbol(
                    name=name,
                    kind=lsp.SymbolKind.Variable,
                    range=_range_for(item),
                    selection_range=_range_for(item),
                )
            )
    return lsp.DocumentSymbol(
        name="SignalGroups",
        kind=lsp.SymbolKind.Class,
        range=_range_for(block),
        selection_range=_range_for(block),
        children=children,
    )


def _timing_symbol(block: Tree) -> lsp.DocumentSymbol:
    children = []
    for item in block.children:
        if isinstance(item, Tree) and item.data == "waveform_table" and item.children:
            name = _text_of(item.children[0]).strip('"')
            children.append(
                lsp.DocumentSymbol(
                    name=name,
                    kind=lsp.SymbolKind.Struct,
                    range=_range_for(item),
                    selection_range=_range_for(item),
                )
            )
    return lsp.DocumentSymbol(
        name="Timing",
        kind=lsp.SymbolKind.Class,
        range=_range_for(block),
        selection_range=_range_for(block),
        children=children,
    )


def _named_block_symbol(block: Tree, label: str) -> lsp.DocumentSymbol:
    name = _name_of_block(block) or label
    return lsp.DocumentSymbol(
        name=name,
        kind=lsp.SymbolKind.Class,
        range=_range_for(block),
        selection_range=_range_for(block),
    )
