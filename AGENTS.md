# STIL Mode — Project Guide

Documentation/reference repo for IEEE Std 1450-1999 STIL (Standard Test Interface Language for Digital Test Vector Data), plus tooling to make STIL a first-class editing language.

## Project scope

| Component | Directory | Status | Language |
|-----------|-----------|--------|----------|
| Lark parser + linter | `parser/` | Planned | Python |
| LSP language server | `server/` | Planned | Python (pygls) |
| Tree-sitter grammar | `tree-sitter-stil/` | Planned | JavaScript → C |
| Emacs major mode | `emacs/stil-mode.el` | Planned | Emacs Lisp |

Single mode file with dual backend: tree-sitter when the grammar library is available, regex-based font-lock as fallback. Activated for `.stil` files.

Dependencies: Phase 1 (parser) is the foundation for Phase 2 (LSP). Phase 3 (tree-sitter) is needed for the TS backend of the Emacs mode.

Detailed plan and task tracking: **`PLAN.md`**

## Repository layout

```
stil-mode/
├── AGENTS.md                  ← you are here (project guide)
├── PLAN.md                    ← implementation plan & task tracking
├── opencode.json              ← OpenCode config (RAG, MCP tools)
├── standards/
│   ├── STIL.md                ← IEEE 1450-1999 standard (~10K lines, authoritative)
│   ├── input.pdf              ← original PDF
│   └── pdf2md.py              ← re-conversion script (markitdown)
├── examples/
│   ├── example1.stil          ← minimal self-contained STIL
│   └── STIL.ELASTIC.*.stil    ← production Cadence Modus ATPG output (3 files)
├── parser/                    ← Lark parser/linter
├── server/                    ← LSP language server
├── tree-sitter-stil/          ← tree-sitter grammar
└── emacs/                             ← Emacs major mode
    └── stil-mode.el                   ← single file: TS when available, regex fallback
```

## STIL language quick reference

- File extension: `.stil`; files begin with `STIL 1.0;`
- Multi-file projects use `Include "filename.stil";`
- Case-sensitive; keywords start uppercase
- Two statement forms: simple (`Keyword tokens;`) and block (`Keyword tokens { ... }`)
- Comments: `//` line comments, `/* block comments */`
- Annotations: `Ann {* text *}` (preserved metadata, not executed)

### Top-level block ordering (IEEE 1450 Table 7)

`STIL` → `Header` → `Signals` → `SignalGroups` → `ScanStructures` → `Spec` → `Timing` → `Selector` → `PatternBurst` → `PatternExec` → `Procedures` → `MacroDefs` → `Pattern`

Optional/unordered: `Include`, `UserKeywords`, `UserFunctions`, `Ann`

### Key syntax notes (non-obvious)

- `\rN` is a repeat operator (e.g. `\r11 Z` = repeat `Z` 11 times)
- `\h`, `\d`, `\w` switch WFC data base (hex/dec/wfc)
- Vector characters (WFCs): `0`=drive-low, `1`=drive-high, `Z`=drive-high-Z, `X`=compare-mask, `L`=expect-low, `H`=expect-high, `T`=expect-high-Z, `P`=pulse, `#`=scan-shift substitution, `%`=fixed substitution
- Drive events: `D`=ForceDown, `U`=ForceUp, `Z`=ForceOff, `P`=ForcePrior, `N`=ForceUnknown
- Compare events: `L`=CompareLow, `H`=CompareHigh, `X`=CompareUnknown, `T`=CompareOff, `G`=ExpectHigh, `Q`=ExpectOff, `M`=Marker
- Waveform labels like `01Z`, `LHTX`, `01ZP` map WFC chars to event sequences in WaveformTables via `/` separator
- Signal direction keywords: `In`, `Out`, `InOut`, `Supply`, `Pseudo`; scan attributes: `ScanIn`, `ScanOut` with chain length
- `MacroDefs` / `Procedures` define reusable vector templates
- `PatternBurst` / `PatternExec` / `Pattern` define test execution hierarchy
- sigref_expr uses `'` quotes with `+`/`-` operators: `'A[0]+B[1..7]'`
- Time expressions use `'` quotes with SI units: `'25ns'`, `'0ns'`
- Signal names can use bracket notation: `A[0..7]`

## STIL examples

- `example1.stil` — Minimal self-contained file (Signals, SignalGroups, Timing, Procedures, Macrodefs, Patterns)
- `STIL.ELASTIC.chip_compression.*.stil` — Production Cadence Modus ATPG for `polaris-lpc`:
  - `signals.stil` — shared signal/group/macro definitions (included by the other two)
  - `scan.ex1.ts1.stil` — scan test section (type = scan)
  - `logic.ex1.ts2.stil` — logic test section (type = logic)

## RAG access

The `opencode.json` configures an `onio-rag-langchain` MCP server (collection `stil`) for STIL domain knowledge queries.

## Source documents for the STIL standard

- **Normative**: `standards/STIL.md` (markdown conversion of the IEEE 1450-1999 PDF, ~10K lines)
- **Original PDF**: `standards/input.pdf`
- **RAG collection `stil`** on the `onio-rag-langchain` MCP — contains the standard plus STARC usage guide and other tutorials. Preferred for targeted queries due to STIL.md size.
- **External reference**: Semi-ATE/STIL on GitHub has a Lark-based STIL parser that may inform grammar design.
