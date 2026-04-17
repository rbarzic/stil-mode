from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from lark import (
    Lark,
    Tree,
    Token,
    UnexpectedInput,
    UnexpectedCharacters,
    UnexpectedToken,
)


GRAMMAR_PATH = Path(__file__).parent / "stil_grammar.lark"


@dataclass
class ParseError:
    line: int
    column: int
    message: str
    token: Optional[str] = None

    def __str__(self):
        loc = f"{self.line}:{self.column}"
        tok = f" (got '{self.token}')" if self.token else ""
        return f"[{loc}] {self.message}{tok}"


@dataclass
class ParseResult:
    tree: Optional[Tree]
    errors: list[ParseError] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def _make_parser() -> Lark:
    grammar = GRAMMAR_PATH.read_text()
    return Lark(
        grammar,
        parser="earley",
        ambiguity="resolve",
        propagate_positions=True,
        maybe_placeholders=False,
    )


_PARSER: Optional[Lark] = None


def get_parser() -> Lark:
    global _PARSER
    if _PARSER is None:
        _PARSER = _make_parser()
    return _PARSER


def parse(text: str) -> ParseResult:
    parser = get_parser()
    try:
        tree = parser.parse(text)
        return ParseResult(tree=tree)
    except UnexpectedCharacters as exc:
        err = _unexpected_chars_error(exc)
        return ParseResult(tree=None, errors=[err])
    except UnexpectedToken as exc:
        err = _unexpected_token_error(exc)
        return ParseResult(tree=None, errors=[err])
    except UnexpectedInput as exc:
        err = _unexpected_input_error(exc)
        return ParseResult(tree=None, errors=[err])


def parse_file(path: str | Path) -> ParseResult:
    return parse(Path(path).read_text())


def _unexpected_chars_error(exc: UnexpectedCharacters) -> ParseError:
    return ParseError(
        line=exc.line,
        column=exc.column,
        message=f"unexpected character",
        token=exc.char,
    )


def _unexpected_token_error(exc: UnexpectedToken) -> ParseError:
    return ParseError(
        line=exc.line,
        column=exc.column,
        message=f"unexpected token, expected one of: {', '.join(exc.accepts or [])}",
        token=str(exc.token),
    )


def _unexpected_input_error(exc: UnexpectedInput) -> ParseError:
    return ParseError(
        line=getattr(exc, "line", 0),
        column=getattr(exc, "column", 0),
        message=str(exc),
    )
