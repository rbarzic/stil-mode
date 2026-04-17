# stil-mode

Editing support for **IEEE Std 1450-1999 STIL** (Standard Test Interface Language for Digital Test Vector Data).

Provides a Lark parser, linter, LSP server, tree-sitter grammar, and an Emacs major mode with dual backend (tree-sitter when available, regex fallback).

## Linter (command-line)

The `stil-lint` script checks STIL files for syntax and semantic errors:

```sh
./stil-lint examples/example1.stil
# examples/example1.stil: OK

./stil-lint broken.stil
# broken.stil:[3:5] unexpected token, expected one of: ...
```

It requires `lark` (the parser library) — install with:

```sh
pip install lark
```

## Emacs major mode

### Basic setup (zero external dependencies)

```elisp
(add-to-list 'load-path "/path/to/stil-mode/emacs")
```

Open a `.stil` file — you get syntax highlighting, indentation, imenu navigation, `//`/`/* */` comment support, and `C-M-a`/`C-M-e` to jump between top-level blocks.

### Tree-sitter backend (optional, Emacs 29+)

If you build and install the tree-sitter grammar, the mode switches to the tree-sitter backend automatically for more accurate highlighting and navigation.

```sh
cd tree-sitter-stil
npm install   # pulls in tree-sitter-cli
tree-sitter generate
```

Then install the compiled parser to your Emacs tree-sitter directory (e.g. `~/.emacs.d/tree-sitter/`).

### LSP via eglot (optional)

Requires `pygls` — install with:

```sh
pip install pygls
```

Then tell eglot how to start the server:

```elisp
(setq stil-lsp-server-command
      '("python3" "-m" "server" "/path/to/stil-mode"))

(add-to-list 'load-path "/path/to/stil-mode/emacs")
```

The server provides real-time diagnostics, completion, hover docs, and go-to-definition (including cross-file via `Include`).

## Python parser / linter API

```python
import sys
sys.path.insert(0, "/path/to/stil-mode")

from parser.parse import parse_file
from parser.lint import lint

result = parse_file("example.stil")
if not result.ok:
    for err in result.errors:
        print(err)
else:
    lr = lint(result.tree)
    for d in lr.diagnostics:
        print(d)
```

## Running tests

```sh
# Parser tests (41 tests)
python3 -m pytest parser/tests/ -v

# Tree-sitter tests (5 corpus tests)
cd tree-sitter-stil && tree-sitter test
```

## What is STIL?

IEEE Std 1450-1999 defines a text format for describing digital test vectors used in semiconductor testing (ATPG, scan, BIST). Key syntax:

- Files start with `STIL 1.0;`
- Case-sensitive; keywords start uppercase
- Comments: `//` line, `/* block */`; annotations: `Ann {* text *}`
- Top-level blocks: `Header` → `Signals` → `SignalGroups` → `ScanStructures` → `Spec` → `Timing` → `Selector` → `PatternBurst` → `PatternExec` → `Procedures` → `MacroDefs` → `Pattern`

## Project layout

```
stil-mode/
├── stil-lint                   Standalone linter CLI
├── parser/                     Lark parser + linter
│   ├── stil_grammar.lark       Grammar definition
│   ├── parse.py                parse() / parse_file()
│   ├── lint.py                 Semantic checks
│   └── tests/test_parser.py    pytest tests
├── server/                     LSP language server (pygls)
│   ├── server.py               Server + diagnostics
│   ├── symbols.py              DocumentSymbol provider
│   ├── completion.py           Context-aware completion
│   ├── hover.py                Hover documentation
│   └── definition.py           Go-to-definition (cross-file)
├── tree-sitter-stil/           Tree-sitter grammar
│   ├── grammar.js              Grammar definition
│   └── test/corpus/basic.txt   Corpus tests
├── emacs/
│   └── stil-mode.el            Emacs major mode
├── examples/                   Example STIL files
│   ├── example1.stil           Minimal self-contained example
│   └── STIL.ELASTIC.*.stil     Production Cadence Modus ATPG output
└── standards/
    └── STIL.md                 IEEE 1450-1999 standard (markdown)
```

## License

MIT
