from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from parser.parse import parse
from parser.lint import lint, Severity, Diagnostic as LintDiagnostic
from server.symbols import collect_symbols
from server.completion import get_completions
from server.hover import get_hover
from server.definition import get_definition


logger = logging.getLogger(__name__)


class StilsLanguageServer(LanguageServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._debounce_timers: dict[str, asyncio.TimerHandle] = {}


server = StilsLanguageServer("stil-language-server", "v0.1.0")


def _severity_to_lsp(severity: Severity) -> lsp.DiagnosticSeverity:
    return {
        Severity.ERROR: lsp.DiagnosticSeverity.Error,
        Severity.WARNING: lsp.DiagnosticSeverity.Warning,
        Severity.INFO: lsp.DiagnosticSeverity.Information,
    }[severity]


def _publish_diagnostics(uri: str, text: str) -> None:
    diagnostics: list[lsp.Diagnostic] = []

    result = parse(text)
    if not result.ok:
        for err in result.errors:
            start = lsp.Position(
                line=max(err.line - 1, 0), character=max(err.column - 1, 0)
            )
            end = lsp.Position(line=start.line, character=start.character + 1)
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(start=start, end=end),
                    message=err.message,
                    severity=lsp.DiagnosticSeverity.Error,
                    source="stil",
                )
            )
        server.publish_diagnostics(uri, diagnostics)
        return

    if result.tree is not None:
        lint_result = lint(result.tree)
        for d in lint_result.diagnostics:
            start = lsp.Position(line=max(d.line - 1, 0), character=d.column)
            end = lsp.Position(line=start.line, character=start.character + 1)
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(start=start, end=end),
                    message=d.message,
                    severity=_severity_to_lsp(d.severity),
                    source="stil",
                )
            )

    server.publish_diagnostics(uri, diagnostics)


def _schedule_diagnostics(uri: str, text: str, delay: float = 0.3) -> None:
    loop = server.loop
    existing = server._debounce_timers.pop(uri, None)
    if existing is not None:
        existing.cancel()
    server._debounce_timers[uri] = loop.call_later(
        delay, lambda: _publish_diagnostics(uri, text)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: lsp.DidOpenTextDocumentParams) -> None:
    _publish_diagnostics(params.text_document.uri, params.text_document.text)


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: lsp.DidChangeTextDocumentParams) -> None:
    changes = params.content_changes
    if changes:
        _schedule_diagnostics(params.text_document.uri, changes[0].text)


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
    existing = server._debounce_timers.pop(params.text_document.uri, None)
    if existing is not None:
        existing.cancel()
    server.publish_diagnostics(params.text_document.uri, [])


def _get_document_text(uri: str) -> str | None:
    doc = server.workspace.get_text_document(uri)
    return doc.source if doc else None


@server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbols(
    params: lsp.DocumentSymbolParams,
) -> list[lsp.DocumentSymbol] | None:
    doc = server.workspace.get_text_document(params.text_document.uri)
    if doc is None:
        return None
    result = parse(doc.source)
    if result.tree is None:
        return None
    return collect_symbols(result.tree)


@server.feature(
    lsp.TEXT_DOCUMENT_COMPLETION,
    lsp.CompletionOptions(trigger_characters=[" "]),
)
def completions(params: lsp.CompletionParams) -> lsp.CompletionList | None:
    uri = params.text_document.uri
    doc = server.workspace.get_text_document(uri)
    if doc is None:
        return None
    result = parse(doc.source)
    if result.tree is None:
        return None
    items = get_completions(
        result.tree, doc.source, params.position.line, params.position.character
    )
    return lsp.CompletionList(is_incomplete=False, items=items)


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(params: lsp.HoverParams) -> lsp.Hover | None:
    uri = params.text_document.uri
    doc = server.workspace.get_text_document(uri)
    if doc is None:
        return None
    result = parse(doc.source)
    if result.tree is None:
        return None
    return get_hover(
        result.tree, doc.source, params.position.line, params.position.character
    )


@server.feature(lsp.TEXT_DOCUMENT_DEFINITION)
def definition(
    params: lsp.DefinitionParams,
) -> list[lsp.Location] | lsp.Location | None:
    uri = params.text_document.uri
    doc = server.workspace.get_text_document(uri)
    if doc is None:
        return None
    result = parse(doc.source)
    if result.tree is None:
        return None
    return get_definition(
        result.tree, doc.source, uri, params.position.line, params.position.character
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    server.start_io()


if __name__ == "__main__":
    main()
