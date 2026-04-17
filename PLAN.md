# STIL Mode — Implementation Plan & Task Tracking

## Overview

Build full editing support for IEEE Std 1450-1999 STIL: parser, linter, LSP server, tree-sitter grammar, and a single Emacs major mode (`stil-mode.el`) with dual backend (tree-sitter when available, regex font-lock as fallback).

## Dependency graph

```
Phase 1 (Parser) ──────────┬─── Phase 2 (LSP Server)
                            └─── Phase 4 (Emacs mode) ────── Phase 3 (Tree-sitter)
```

- Phase 1 (Parser) is the foundation — the LSP server reuses it
- Phase 3 (Tree-sitter) is needed for the TS backend of the Emacs mode (Phase 4)
- Phase 4 (Emacs mode) can be built incrementally: regex backend first, then add TS backend after Phase 3

## Estimated complexity per phase

| Phase | Effort | Notes |
|-------|--------|-------|
| 1. Parser/Linter | High | Largest effort: formal grammar (~500 rules), semantic checks |
| 2. LSP Server | Medium | Builds on parser; pygls is well-documented |
| 3. Tree-sitter | Medium | Grammar translation from Lark; tree-sitter quirks |
| 4. Emacs mode | Medium | Dual backend: regex + TS queries, indentation, navigation |

---

## Phase 1: Lark Parser/Linter

**Goal**: A Python parser that accepts any valid IEEE 1450-1999 STIL file, produces an AST, and runs lint checks.

### Task breakdown

- [x] **1.1** Define formal Lark grammar (`parser/stil_grammar.lark`)
  - [ ] Lexer terminals: keywords, identifiers, string literals, time expressions, WFC chars, sigref expressions, annotations, comments
  - [ ] Parser rules for all top-level blocks: `STIL`, `Header`, `Include`, `UserKeywords`, `UserFunctions`, `Ann`, `Signals`, `SignalGroups`, `ScanStructures`, `Spec`, `Selector`, `Timing`, `PatternBurst`, `PatternExec`, `Procedures`, `MacroDefs`, `Pattern`
  - [ ] Parser rules for nested constructs: WaveformTable, Waveforms, SubWaveforms, Pattern statements (V/F, C, W, Loop, MatchLoop, Shift, Call, Macro, Goto, Stop, Iddq, etc.)
  - [ ] Handle tricky lexical elements:
    - `Ann {* ... *}` annotation blocks (custom delimiter)
    - sigref_expr in single quotes: `'sig1+sig2[0..7]'`
    - Time expressions in single quotes: `'25.0ns'`
    - `\rN` repeat operators in vector data
    - `\h`, `\d`, `\w` base switches in vector data
    - Event lists with `/` separator: `D/U/Z`
    - UserKeywords/UserFunctions extending the keyword set
  - [ ] Strategy: use Lark's `Earley` parser for flexibility with context-sensitive constructs; refine to `LALR` if achievable

- [x] **1.2** Implement parser entry point (`parser/parse.py`)
  - [ ] `parse(text: str) -> Tree` — parse STIL source to Lark tree
  - [ ] `parse_file(path: str) -> Tree` — parse from file path
  - [ ] `format_errors(tree, text) -> list[ParseError]` — collect syntax errors with line/column info

- [x] **1.3** Implement linter (`parser/lint.py`)
  - [ ] Block ordering validation (Table 7 order)
  - [ ] Duplicate signal/signal-group/pattern name detection
  - [ ] WFC uniqueness per signal per WaveformTable
  - [ ] Undefined references (signal names, group names, WaveformTable names, pattern names, macro/procedure names)
  - [ ] WFC character validity (alphanumeric + `#` + `%`)
  - [ ] Signal direction consistency with waveform events (drive vs compare)
  - [ ] ScanIn/ScanOut length consistency
  - [ ] Include file existence check (warning)
  - [ ] Lint severity levels: error, warning, info
  - [ ] `lint(tree: Tree, text: str, path: str) -> list[Diagnostic]`

- [x] **1.4** Parser test suite (`parser/tests/`)
  - [ ] Unit tests for each grammar rule
  - [ ] Integration tests parsing all files in `examples/`
  - [ ] Negative tests for common syntax errors
  - [ ] Framework: `pytest`

### Key grammar challenges and solutions

| Challenge | Solution |
|-----------|----------|
| `Ann {* ... *}` blocks with arbitrary content | Custom lexer state or regex terminal: `ANN_BODY: /\{\*.*?\*\}/s` |
| Single-quoted sigref_expr and time_expr | Terminal `SINGLE_QUOTED: /'[^']*'/` with post-parse validation |
| `\rN` repeat in vector data | Terminal `REPEAT_OP: /\\r[0-9]+/` |
| Keywords vs identifiers (case-sensitive) | Explicit keyword list in Lark; `NAME` terminal for identifiers |
| WFC data strings (unquoted, mixed characters) | Custom terminal pattern for vector data after `=` |
| UserKeywords extending keyword set | Two-pass: first pass collects UserKeywords, second pass parses with extended set |
| Block vs simple statement ambiguity | Lark handles via lookahead; `?` optional rules for optional braces |

---

## Phase 2: Language Server (LSP)

**Goal**: A pygls-based LSP server providing real-time diagnostics, completion, hover, and go-to-definition for `.stil` files.

### Task breakdown

- [x] **2.1** Server skeleton (`server/server.py`)
  - [x] pygls `LanguageServer` subclass
  - [x] Document synchronization (full text)
  - [x] `.stil` file detection
  - [x] Stdio transport (for editor integration)

- [x] **2.2** Diagnostics (integrated in `server/server.py`)
  - [x] On-change: re-parse document, run linter, publish diagnostics
  - [x] Debounce rapid changes (300ms)
  - [x] Map parser/lint errors to LSP Diagnostic objects (range, severity, message, source)

- [x] **2.3** Document symbols (`server/symbols.py`)
  - [x] Extract top-level blocks as DocumentSymbol hierarchy
  - [x] Signal names, signal group names, WaveformTable names, pattern names, labels as children

- [x] **2.4** Completion (`server/completion.py`)
  - [x] Keyword completion (context-aware):
    - Top-level: `Signals`, `SignalGroups`, `Timing`, `Pattern`, etc.
    - Inside Signals block: `In`, `Out`, `InOut`, `Supply`, `Pseudo`, `ScanIn`, `ScanOut`
    - Inside Waveforms block: event names (`ForceDown`, `ForceUp`, `ForceOff`, `CompareHigh`, etc.)
    - Inside Pattern block: `V`, `C`, `W`, `Loop`, `Call`, `Macro`, `Shift`, `Goto`, `Stop`
  - [x] Name completion: signal names, group names, WaveformTable names, pattern names, macro/procedure names (from parsed AST)

- [x] **2.5** Hover (`server/hover.py`)
  - [x] Hover on keywords → standard clause reference
  - [x] Hover on signal names → signal type info
  - [x] Hover on WaveformTable name → period info
  - [x] Hover on events → event definition

- [x] **2.6** Go-to definition (`server/definition.py`)
  - [x] Signal name → Signals block definition
  - [x] SignalGroup name → SignalGroups block definition
  - [x] WaveformTable name → Timing/WaveformTable definition
  - [x] Pattern name → Pattern block definition
  - [x] Cross-file via Include resolution (follows Include paths, parses included files)

- [x] **2.7** Configuration (integrated in `server/server.py` and `emacs/stil-mode.el`)
  - [x] Lint level via server startup
  - [x] Include path resolution (relative to current file)
  - [x] `stil-lsp-server-command` custom variable in Emacs

---

## Phase 3: Tree-sitter Grammar ✅

**Goal**: A tree-sitter grammar for STIL enabling fast incremental parsing for editors (Emacs, Neovim, Helix).

**Status**: Complete. All 4 example files parse with 0 errors. 5/5 test corpus tests pass.

### Key design decisions

- **No `word` declaration**: Avoids single-letter keyword conflicts (event chars, default state chars)
- **`wfc_label` terminal**: Unified `/[A-Za-z0-9]+/` for WFC waveform labels, avoiding name/wfc_list ambiguity
- **`event_char` terminal**: Single-char events as regex `/[DPUZNLTVMABFRGHQ?lhtv]/`, multi-word events as aliased keywords
- **`default_state_char` terminal**: `/[UDZ]/` to avoid keyword conflicts
- **`ann_body` regex**: `/\{\*[^*]*\*+(?:[^}*][^*]*\*+)*\}/` handles multi-line annotations without dotAll flag
- **`wfc_tail` / `_name_or_event`**: Merged event/subwf interpretation via declared conflict

**Goal**: A tree-sitter grammar for STIL enabling fast incremental parsing for editors (Emacs, Neovim, Helix).

### Task breakdown

- [x] **3.1** Grammar definition (`tree-sitter-stil/grammar.js`)
  - [x] Map STIL syntax to tree-sitter rules
  - [x] Rules mirror the Lark grammar structure but in tree-sitter DSL
  - [x] Key rules:
    - `source_file`: `STIL` float `;` + top-level blocks
    - `signals_block`, `signalgroups_block`, `timing_block`, `pattern_block`, etc.
    - `vector_stmt`, `condition_stmt`, `loop_stmt`, `shift_stmt`
    - `waveform_table`, `waveform_entry`, `wfc_block`
    - `sigref_expr` (single-quoted signal expressions)
    - `time_expr` (single-quoted time values)
    - `ann_body` (`{* ... *}` with cross-newline matching)
    - `vec_data_chunk` (vector data with `\rN`, `\h`, `\d`, `\w`)
  - [x] Handle conflicts:
    - `sig_or_group` vs `_name_or_string` (declared conflict)
    - `wfc_tail` vs `_name_or_event` (declared conflict)
    - `wfc_label` as unified alphanumeric terminal to avoid name/wfc_list conflicts
    - Event chars as regex terminal (`event_char`) to avoid keyword conflicts
    - Default state chars as regex terminal to avoid keyword conflicts

- [x] **3.2** Package setup (`tree-sitter-stil/package.json`)
  - [x] Name: `tree-sitter-stil`
  - [x] Tree-sitter configuration with scope `source.stil` and file-types `["stil"]`

- [x] **3.3** Test corpus (`tree-sitter-stil/test/corpus/`)
  - [x] 5 test cases: minimal file, signals, signal groups, annotations, spec/selector

- [x] **3.4** Build & verify
  - [x] `tree-sitter generate` → C parser (ABI 14)
  - [x] `tree-sitter test` → 5/5 pass
  - [x] `tree-sitter parse examples/*.stil` → 0 errors on all 4 files

---

## Phase 4: Emacs Major Mode (`stil-mode.el`)

**Goal**: A single Emacs major mode for `.stil` files with dual backend. When the `tree-sitter-stil` grammar library is available, it uses tree-sitter for font-lock, indentation, and navigation. When it is not available, it falls back to regex-based font-lock — so basic syntax highlighting always works.

### Task breakdown

- [x] **4.1** Mode skeleton (`emacs/stil-mode.el`)
  - [x] `stil-mode` derived from `prog-mode`
  - [x] Association with `.stil` files via `auto-mode-alist`
  - [x] Runtime detection: `stil--ts-available-p` checks tree-sitter grammar
  - [x] If TS available → activate tree-sitter backend
  - [x] If TS not available → activate regex font-lock backend

- [x] **4.2** Syntax table (shared by both backends)
  - [x] `//` → comment start, `/* */` → comment block
  - [x] `{ }` → delimiters (parenthesis class)
  - [x] `;` → statement terminator
  - [x] Single/double quotes handled

- [x] **4.3** Regex font-lock backend (fallback)
  - [x] Level 1: top-level keywords, block keywords, pattern keywords
  - [x] Level 2: type keywords (direction, termination, etc.)
  - [x] Level 3: event keywords (ForceDown, CompareHigh, etc.)
  - [x] Level 4: abbreviations (V, W, C, F)
  - [x] Level 5: literals (time/sigref expressions, strings, repeat ops)
  - [x] Level 6: labels (UPPER_CASE:)

- [x] **4.4** Tree-sitter backend (primary when available)
  - [x] Font-lock rules: keywords, types, events, strings, constants, names, comments, annotations
  - [x] Imenu: extract block names via `stil-ts-imenu-create-index`

- [x] **4.5** Indentation rules
  - [x] Regex backend: brace-counting indentation (`stil-indent-line`)
  - [x] TS backend: tree-sitter simple indent rules

- [x] **4.6** Imenu support
  - [x] Regex backend: `stil-imenu-generic-expression`
  - [x] TS backend: `stil-ts-imenu-create-index`

- [x] **4.7** Movement commands
  - [x] `C-M-a` / `C-M-e`: move between top-level blocks (`stil-beginning-of-block`, `stil-end-of-block`)
  - [x] `C-M-f` / `C-M-b`: brace matching via standard syntax table

- [x] **4.8** Flycheck/flymake integration
  - [x] Flymake backend: runs Python parser/linter on save (`stil-flymake-lint`)
  - [x] Controlled by `stil-use-flymake` custom variable

- [x] **4.9** LSP integration
  - [x] eglot auto-configuration via `eglot-server-programs`
  - [x] `stil-lsp-server-command` custom variable for server path

- [x] **4.10** Which-function support
  - [x] `stil-which-function` returns current block name for mode line
  - [x] Wired to `which-func-functions` buffer-locally

- [x] **4.11** Installation
  - [x] Regex backend works out of the box (no external dependencies)
  - [x] TS backend: build `tree-sitter-stil` grammar, install to Emacs tree-sitter path
  - [x] LSP: `python3 -m server.server` (or configure `stil-lsp-server-command`)
