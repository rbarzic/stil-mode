from __future__ import annotations

import logging
from pathlib import Path
from urllib.parse import urlparse, unquote

from lsprotocol import types as lsp
from lark import Tree, Token

from parser.parse import parse
from parser.lint import _text_of

logger = logging.getLogger(__name__)


def _line_of(node) -> int:
    if isinstance(node, Tree):
        meta = getattr(node, "meta", None)
        if meta and hasattr(meta, "line"):
            return max(meta.line - 1, 0)
    return 0


def _range_for_line(node) -> lsp.Range:
    line = _line_of(node)
    return lsp.Range(
        start=lsp.Position(line=line, character=0),
        end=lsp.Position(line=line, character=0),
    )


def _word_at(text: str, line: int, char: int) -> str:
    lines = text.split("\n")
    if line >= len(lines):
        return ""
    l = lines[line]
    if char >= len(l):
        char = len(l) - 1
    start = char
    while start > 0 and (l[start - 1].isalnum() or l[start - 1] == "_"):
        start -= 1
    end = char
    while end < len(l) and (l[end].isalnum() or l[end] == "_"):
        end += 1
    return l[start:end]


def _parse_include_paths(tree: Tree) -> list[str]:
    paths = []
    if tree.data != "start":
        return paths
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data == "include_stmt" and inner.children:
            inc_path = _text_of(inner.children[0]).strip('"')
            if inc_path:
                paths.append(inc_path)
    return paths


def _uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    return Path(unquote(parsed.path))


def _collect_all_trees(
    tree: Tree, base_dir: Path, seen: set[str] | None = None
) -> dict[str, tuple[Tree, str]]:
    if seen is None:
        seen = set()
    result = {}
    result[str(base_dir)] = (tree, str(base_dir))

    for inc_rel in _parse_include_paths(tree):
        inc_path = (base_dir / inc_rel).resolve()
        inc_str = str(inc_path)
        if inc_str in seen:
            continue
        if not inc_path.exists():
            continue
        seen.add(inc_str)
        try:
            inc_result = parse(inc_path.read_text())
            if inc_result.tree is not None:
                result[inc_str] = (inc_result.tree, inc_str)
                sub = _collect_all_trees(inc_result.tree, inc_path.parent, seen)
                result.update(sub)
        except Exception:
            logger.debug("Failed to parse include: %s", inc_path)
    return result


def get_definition(
    tree: Tree, text: str, uri: str, line: int, col: int
) -> list[lsp.Location] | lsp.Location | None:
    word = _word_at(text, line, col)
    if not word:
        return None

    if tree.data != "start":
        return None

    loc = _find_signal_def(tree, uri, word)
    if loc:
        return [loc]

    loc = _find_signalgroup_def(tree, uri, word)
    if loc:
        return [loc]

    loc = _find_wft_def(tree, uri, word)
    if loc:
        return [loc]

    loc = _find_pattern_def(tree, uri, word)
    if loc:
        return [loc]

    loc = _find_proc_or_macro_def(tree, uri, word, "procedures_block")
    if loc:
        return [loc]

    loc = _find_proc_or_macro_def(tree, uri, word, "macrodefs_block")
    if loc:
        return [loc]

    base_dir = _uri_to_path(uri).parent
    all_trees = _collect_all_trees(tree, base_dir)
    for path_str, (inc_tree, _) in all_trees.items():
        if path_str == str(base_dir):
            continue
        try:
            inc_uri = Path(path_str).as_uri()
        except ValueError:
            continue

        loc = _find_signal_def(inc_tree, inc_uri, word)
        if loc:
            return [loc]
        loc = _find_signalgroup_def(inc_tree, inc_uri, word)
        if loc:
            return [loc]
        loc = _find_wft_def(inc_tree, inc_uri, word)
        if loc:
            return [loc]
        loc = _find_pattern_def(inc_tree, inc_uri, word)
        if loc:
            return [loc]
        loc = _find_proc_or_macro_def(inc_tree, inc_uri, word, "procedures_block")
        if loc:
            return [loc]
        loc = _find_proc_or_macro_def(inc_tree, inc_uri, word, "macrodefs_block")
        if loc:
            return [loc]

    return None


def _find_signal_def(tree: Tree, uri: str, name: str) -> lsp.Location | None:
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != "signals_block":
            continue
        for sig in inner.children:
            if not isinstance(sig, Tree) or not sig.children:
                continue
            sig_name = _text_of(sig.children[0]).strip('"')
            if sig_name == name:
                return lsp.Location(uri=uri, range=_range_for_line(sig))
    return None


def _find_signalgroup_def(tree: Tree, uri: str, name: str) -> lsp.Location | None:
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != "signalgroups_block":
            continue
        for sg in inner.children:
            if not isinstance(sg, Tree) or not sg.children:
                continue
            sg_name = _text_of(sg.children[0]).strip('"')
            if sg_name == name:
                return lsp.Location(uri=uri, range=_range_for_line(sg))
    return None


def _find_wft_def(tree: Tree, uri: str, name: str) -> lsp.Location | None:
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
                wft_name = _text_of(item.children[0]).strip('"')
                if wft_name == name:
                    return lsp.Location(uri=uri, range=_range_for_line(item))
    return None


def _find_pattern_def(tree: Tree, uri: str, name: str) -> lsp.Location | None:
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != "pattern_block" or not inner.children:
            continue
        pat_name = _text_of(inner.children[0]).strip('"')
        if pat_name == name:
            return lsp.Location(uri=uri, range=_range_for_line(inner))
    return None


def _find_proc_or_macro_def(
    tree: Tree, uri: str, name: str, block_type: str
) -> lsp.Location | None:
    for child in tree.children:
        if not isinstance(child, Tree) or child.data != "toplvl":
            continue
        inner = child.children[0]
        if inner.data != block_type:
            continue
        for item in inner.children:
            if isinstance(item, Tree) and item.children:
                def_name = _text_of(item.children[0]).strip('"')
                if def_name == name:
                    return lsp.Location(uri=uri, range=_range_for_line(item))
    return None
