# stil-mode

Editing support for **IEEE Std 1450-1999 STIL** (Standard Test Interface Language for Digital Test Vector Data).

## Components

| Component | Directory | Language | Description |
|-----------|-----------|----------|-------------|
| Lark parser + linter | `parser/` | Python | Parses any valid STIL file, runs semantic checks |
| LSP language server | `server/` | Python (pygls) | Diagnostics, completion, hover, go-to-definition |
| Tree-sitter grammar | `tree-sitter-stil/` | JavaScript → C | Fast incremental parsing for editors |
| Emacs major mode | `emacs/stil-mode.el` | Emacs Lisp | Dual backend: tree-sitter when available, regex fallback |

## Quick start

### Emacs (regex backend — zero dependencies)

Add `emacs/` to your `load-path` and open a `.stil` file:

```elisp
(add-to-list 'load-path "/path/to/stil-mode/emacs")
```

Syntax highlighting, indentation, imenu navigation, and comment support work immediately.

### Emacs (tree-sitter backend)

Build the grammar first:

```sh
cd tree-sitter-stil
npm install
tree-sitter generate
cc -shared -fPIC src/parser.c -o stil.so
```

Then install `stil.so` to your Emacs tree-sitter path. The mode auto-detects the grammar and switches to the tree-sitter backend.

### Emacs (LSP integration)

Install pygls, then configure eglot:

```elisp
(setq stil-lsp-server-command '("python3" "-m" "server.server"))
```

Or start the server manually:

```sh
cd /path/to/stil-mode
python3 -m server.server
```

### Parser / Linter (Python)

```python
from parser.parse import parse, parse_file
from parser.lint import lint

result = parse_file("examples/example1.stil")
if result.ok:
    lint_result = lint(result.tree)
    for d in lint_result.diagnostics:
        print(d)
```

### Running tests

```sh
# Parser tests
python3 -m pytest parser/tests/ -v

# Tree-sitter tests
cd tree-sitter-stil && tree-sitter test
```

## STIL language reference

- File extension: `.stil`; files begin with `STIL 1.0;`
- Case-sensitive; keywords start uppercase
- Comments: `//` line, `/* block */`; annotations: `Ann {* text *}`
- Top-level block order: `Header` → `Signals` → `SignalGroups` → `ScanStructures` → `Spec` → `Timing` → `Selector` → `PatternBurst` → `PatternExec` → `Procedures` → `MacroDefs` → `Pattern`

## Project layout

```
stil-mode/
├── parser/                     Lark parser + linter
│   ├── stil_grammar.lark       Grammar definition
│   ├── parse.py                parse() / parse_file()
│   ├── lint.py                 Semantic checks
│   └── tests/test_parser.py    41 pytest tests
├── server/                     LSP language server
│   ├── server.py               pygls server + diagnostics
│   ├── symbols.py              DocumentSymbol provider
│   ├── completion.py           Context-aware completion
│   ├── hover.py                Hover documentation
│   └── definition.py           Go-to-definition (cross-file)
├── tree-sitter-stil/           Tree-sitter grammar
│   ├── grammar.js              Grammar definition
│   ├── package.json            npm package config
│   └── test/corpus/basic.txt   5 corpus tests
├── emacs/
│   └── stil-mode.el            Emacs major mode (dual backend)
├── examples/                   Example STIL files
│   ├── example1.stil           Minimal self-contained example
│   └── STIL.ELASTIC.*.stil     Production Cadence Modus ATPG output
└── standards/
    └── STIL.md                 IEEE 1450-1999 standard (markdown)
```

## License

MIT
