from __future__ import annotations

from lsprotocol import types as lsp
from lark import Tree, Token

from parser.lint import _text_of


_KEYWORD_DOCS: dict[str, str] = {
    "STIL": "STIL 1.0; — File header declaring this as a Standard Test Interface Language file (IEEE Std 1450-1999).",
    "Header": "Header { Title ...; Date ...; Source ...; History { ... } } — File metadata block.",
    "Signals": "Signals { name Direction; ... } — Declares all DUT signal pins with direction (In, Out, InOut, Supply, Pseudo).",
    "SignalGroups": "SignalGroups { name = 'sig1+sig2'; ... } — Named groups of signals using sigref expressions.",
    "ScanStructures": "ScanStructures { ScanChain name { ... } } — Defines scan chain topology.",
    "Spec": "Spec name { Category name { var = 'time'; } } — Specification values (min/typ/max timing).",
    "Selector": "Selector name { var Min|Typ|Max; } — Selects spec corner values.",
    "Timing": "Timing name { WaveformTable name { ... } } — Timing and waveform definitions.",
    "WaveformTable": "WaveformTable name { Period 'time'; Waveforms { ... } } — Defines cycle timing and waveform shapes.",
    "Period": "Period 'time'; — Sets the cycle period for a WaveformTable.",
    "Waveforms": "Waveforms { signal { wfc { 'time' event; } } } — Maps WFC characters to event sequences per signal.",
    "SubWaveforms": "SubWaveforms { name: Duration 'time' { ... } } — Defines sub-waveform templates.",
    "PatternBurst": "PatternBurst name { PatList { pattern; ... } } — Ordered list of patterns to execute.",
    "PatternExec": "PatternExec name { Timing name; PatternBurst name; } — Binds timing, spec, and burst for execution.",
    "Procedures": "Procedures name { procname { V { ... } } } — Reusable vector procedures.",
    "MacroDefs": "MacroDefs name { macroname { V { ... } } } — Reusable vector macro templates.",
    "Pattern": "Pattern name { W wft; V { ... } } — Test pattern with vectors.",
    "Include": 'Include "filename"; — Includes another STIL file.',
    "Ann": "Ann {* text *} — Annotation (preserved metadata, not executed).",
    "V": "V { sig = data; } — Vector statement: applies stimulus/compare data to signals for one cycle.",
    "C": "C { sig = data; } — Condition statement: sets up signal state (no cycle advancement).",
    "W": "W wftname; — Selects active WaveformTable for subsequent vectors.",
    "Loop": "Loop N { ... } — Repeats enclosed pattern statements N times.",
    "MatchLoop": "MatchLoop N { ... BreakPoint { ... } } — Repeats until match or breakpoint.",
    "Call": "Call procname; or Call procname { sig = data; } — Invokes a procedure.",
    "Macro": "Macro macroname; or Macro macroname { sig = data; } — Expands a macro definition.",
    "Goto": "Goto label; — Jumps to a labeled statement within the pattern.",
    "Stop": "Stop; — Halts pattern execution.",
    "Shift": "Shift { ... } — Scan shift operations.",
    "BreakPoint": "BreakPoint; — Marks a breakpoint in MatchLoop.",
    "ScanChain": "ScanChain name; — Selects active scan chain.",
    "IDDQ": "IDDQ TestPoint; — IDDQ measurement point.",
}

_SIGNAL_DIR_DOCS = {
    "In": "Input signal (drive from tester to DUT).",
    "Out": "Output signal (compare from DUT to tester).",
    "InOut": "Bidirectional signal.",
    "Supply": "Power/ground supply pin.",
    "Pseudo": "Pseudo-signal (virtual, not physical pin).",
}


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


def get_hover(tree: Tree, text: str, line: int, col: int) -> lsp.Hover | None:
    word = _word_at(text, line, col)
    if not word:
        return None

    if word in _KEYWORD_DOCS:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.PlainText,
                value=_KEYWORD_DOCS[word],
            )
        )

    if word in _SIGNAL_DIR_DOCS:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.PlainText,
                value=_SIGNAL_DIR_DOCS[word],
            )
        )

    if tree.data != "start":
        return None

    signal_info = _find_signal_info(tree, word)
    if signal_info:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.PlainText,
                value=signal_info,
            )
        )

    return None


def _find_signal_info(tree: Tree, name: str) -> str | None:
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
            if sig_name == name and len(sig.children) >= 2:
                direction = _text_of(sig.children[1]).strip('"')
                return f"Signal `{name}` — Direction: {direction}"
    return None
