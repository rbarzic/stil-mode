;;; stil-mode.el --- Major mode for IEEE Std 1450-1999 STIL files  -*- lexical-binding: t; -*-

;; Copyright (C) 2024

;; Author: STIL Mode Contributors
;; Keywords: languages, stil, ieee-1450, atpg, test
;; Version: 0.1.0
;; Package-Requires: ((emacs "28.1"))

;; This file is not part of GNU Emacs.

;; Commentary:

;; A major mode for editing STIL (Standard Test Interface Language for
;; Digital Test Vector Data) files per IEEE Std 1450-1999.
;;
;; When the `tree-sitter-stil' grammar library is available, uses
;; tree-sitter for font-lock, indentation, and navigation.  Otherwise,
;; falls back to regex-based font-lock — so basic syntax highlighting
;; always works out of the box.
;;
;; Features:
;;   - Syntax highlighting (keywords, events, types, strings, annotations)
;;   - Imenu navigation for top-level blocks
;;   - Basic indentation
;;   - Comment handling (// and /* */)
;;   - Integration with LSP (eglot/lsp-mode) via the STIL language server

;;; Code:

(require 'Treesit nil t)              ; tree-sitter (Emacs 29+)
(declare-function treesit-ready-p "treesit" (lang &optional quiet))
(declare-function treesit-parser-create "treesit" (lang &optional buf))
(declare-function treesit-node-children "treesit.c" (node &optional named))
(declare-function treesit-node-type "treesit.c" (node))
(declare-function treesit-node-text "treesit.c" (node &optional property))
(declare-function treesit-node-start "treesit.c" (node))
(declare-function treesit-buffer-root-node "treesit" (&optional lang))
(declare-function treesit-major-mode-setup "treesit" ())
(declare-function treesit-font-lock-enable "treesit" ())
(declare-function treesit-simple-indent-rules "treesit" (lang rules))
(defvar eglot-server-programs)
(declare-function json-read-from-string "json" (string))
(eval-when-compile (require 'subr-x))

;; ── Customization ───────────────────────────────────────────────

(defgroup stil nil
  "Major mode for IEEE Std 1450-1999 STIL files."
  :group 'languages
  :prefix "stil-")

(defcustom stil-indent-offset 2
  "Number of spaces for each indentation level in STIL."
  :type 'integer
  :group 'stil)

;; ── Syntax table (shared) ───────────────────────────────────────

(defvar stil-syntax-table
  (let ((table (make-syntax-table)))
    (modify-syntax-entry ?/  ". 124" table)
    (modify-syntax-entry ?*  ". 23b" table)
    (modify-syntax-entry ?\n "> "    table)
    (modify-syntax-entry ?{  "(}"    table)
    (modify-syntax-entry ?}  "){"    table)
    (modify-syntax-entry ?\; "."     table)
    (modify-syntax-entry ?=  "."     table)
    (modify-syntax-entry ?+  "."     table)
    (modify-syntax-entry ?-  "."     table)
    (modify-syntax-entry ?:  "."     table)
    (modify-syntax-entry ?#  "_"     table)
    (modify-syntax-entry ?%  "_"     table)
    (modify-syntax-entry ?\\ "\\"    table)
    table)
  "Syntax table for STIL mode.")

;; ── Keywords ────────────────────────────────────────────────────

(defconst stil-top-level-keywords
  '("STIL" "Header" "Signals" "SignalGroups" "ScanStructures"
    "Spec" "Timing" "Selector" "PatternBurst" "PatternExec"
    "Procedures" "MacroDefs" "Pattern" "Include" "UserKeywords"
    "UserFunctions" "Ann"))

(defconst stil-type-keywords
  '("In" "Out" "InOut" "Supply" "Pseudo" "ScanIn" "ScanOut"
    "DataBitCount" "Termination" "DefaultState" "Base" "Alignment"
    "Hex" "Dec" "MSB" "LSB"))

(defconst stil-event-keywords
  '("ForceDown" "ForceUp" "ForceOff" "ForcePrior" "ForceUnknown"
    "CompareLow" "CompareHigh" "CompareUnknown" "CompareOff"
    "CompareValid" "CompareLowWindow" "CompareHighWindow"
    "CompareOffWindow" "CompareValidWindow" "ExpectLow" "ExpectHigh"
    "ExpectOff" "Marker" "LogicLow" "LogicHigh" "LogicZ" "Unknown"
    "TerminateHigh" "TerminateLow" "TerminateOff" "TerminateUnknown"))

(defconst stil-block-keywords
  '("WaveformTable" "Waveforms" "SubWaveforms" "Period"
    "InheritWaveformTable" "PatList" "ScanChain" "Category"
    "Variable" "Min" "Typ" "Max" "Meas" "History"
    "Title" "Date" "Source" "IfNeed" "Duration"
    "SignalGroups" "Start" "Stop" "TimeUnit"))

(defconst stil-pattern-keywords
  '("Vector" "Condition" "Loop" "MatchLoop" "Infinite"
    "Call" "Macro" "Goto" "BreakPoint" "Shift" "IDDQ" "TestPoint"))

;; ── Regex font-lock backend (fallback) ──────────────────────────

(defvar stil-font-lock-keywords
  `((,(concat "\\<" (regexp-opt stil-top-level-keywords) "\\>")
     1 font-lock-keyword-face)
    (,(concat "\\<" (regexp-opt stil-type-keywords) "\\>")
     1 font-lock-type-face)
    (,(concat "\\<" (regexp-opt stil-event-keywords) "\\>")
     1 font-lock-builtin-face)
    (,(concat "\\<" (regexp-opt stil-block-keywords) "\\>")
     1 font-lock-keyword-face)
    (,(concat "\\<" (regexp-opt stil-pattern-keywords) "\\>")
     1 font-lock-keyword-face)
    (,(concat "\\<" (regexp-opt '("V" "W" "C" "F")) "\\>")
     1 font-lock-keyword-face)
    ("\\('\\(?:[^']\\|\\\\'\\)*'\\)" 1 font-lock-string-face)
    ("\\(\"[^\"]*\"\\)" 1 font-lock-string-face)
    ("\\(\\b[A-Z_][A-Z0-9_]*:\\)" 1 font-lock-label-face)
    ("\\(\\\\r[0-9]+\\)" 1 font-lock-constant-face)
    ("\\(\\\\[hdwH DW][A-Za-z0-9]*\\)" 1 font-lock-constant-face))
  "Font-lock keywords for STIL mode (regex backend).")

;; ── Tree-sitter backend ─────────────────────────────────────────

(defvar stil-ts-font-lock-rules
  (when (fboundp 'treesit-font-lock-rules)
    (treesit-font-lock-rules
     :language 'stil
     :feature 'keyword
     `([,(append stil-top-level-keywords stil-block-keywords stil-pattern-keywords '("V" "W" "C" "F"))]
       @ font-lock-keyword-face)

     :language 'stil
     :feature 'type
     `([,stil-type-keywords] @ font-lock-type-face)

     :language 'stil
     :feature 'event
     `([,stil-event-keywords] @ font-lock-builtin-face)

     :language 'stil
     :feature 'string
     `((sigref_expr) @ font-lock-string-face
       (time_expr) @ font-lock-string-face
       (string) @ font-lock-string-face)

     :language 'stil
     :feature 'constant
     `((integer) @ font-lock-constant-face
       (repeat_op) @ font-lock-constant-face
       (wfc_label) @ font-lock-variable-name-face)

     :language 'stil
     :feature 'name
     `((name) @ font-lock-variable-name-face
       (waveform_table name: (name)) @ font-lock-function-name-face
       (pattern_block name: (name)) @ font-lock-function-name-face
       (proc_def name: (name)) @ font-lock-function-name-face
       (macro_def name: (name)) @ font-lock-function-name-face)

     :language 'stil
     :feature 'comment
     `((line_comment) @ font-lock-comment-face
       (block_comment) @ font-lock-comment-face)

     :language 'stil
     :feature 'annotation
     `((ann_body) @ font-lock-doc-face)))
  "Tree-sitter font-lock rules for STIL mode.")

;; ── Imenu ───────────────────────────────────────────────────────

(defvar stil-imenu-generic-expression
  `(("Pattern"      "^\\s-*Pattern\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)\\s-*{" 1)
    ("Procedure"    "^\\s-*Procedures?\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)\\s-*{" 1)
    ("Macro"        "^\\s-*MacroDefs?\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)\\s-*{" 1)
    ("WaveformTable" "^\\s-*WaveformTable\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)" 1)
    ("PatternBurst" "^\\s-*PatternBurst\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)" 1)
    ("Spec"         "^\\s-*Spec\\s-+\\([A-Za-z_][A-Za-z0-9_]*\\)" 1)
    ("Signals"      "^\\s-*Signals\\s-*{" nil)
    ("SignalGroups" "^\\s-*SignalGroups\\s-*{" nil)
    ("Timing"       "^\\s-*Timing\\s-*{" nil))
  "Imenu expression for STIL mode.")

(defun stil-ts-imenu-node-p (node)
  "Return non-nil if NODE is a named block that should appear in imenu."
  (member (treesit-node-type node)
          '("pattern_block" "procedures_block" "macrodefs_block"
            "waveform_table" "patternburst_block" "spec_block"
            "signals_block" "signalgroups_block" "timing_block")))

(defun stil-ts-imenu-create-index (&optional node)
  "Create imenu index from tree-sitter NODE."
  (let* ((node (or node (treesit-buffer-root-node 'stil)))
         (children (treesit-node-children node))
         index)
    (dolist (child children)
      (when (member (treesit-node-type child) '("top_level_block"))
        (let* ((inner (car (treesit-node-children child)))
               (type (treesit-node-type inner)))
          (when ( stil-ts-imenu-node-p inner)
            (let* ((name-node (car (treesit-node-children inner)))
                   (name (if name-node
                             (treesit-node-text name-node)
                           type))
                   (pos (treesit-node-start inner)))
              (push (cons name pos) index))))))
    (nreverse index)))

;; ── Indentation ─────────────────────────────────────────────────

(defun stil-indent-line ()
  "Indent current line for STIL mode."
  (interactive)
  (let* ((indent 0)
         (bol (line-beginning-position)))
    (save-excursion
      (goto-char bol)
      (while (re-search-backward "[{}]" nil t)
        (if (eq (char-after) ?{)
            (cl-incf indent stil-indent-offset)
          (cl-decf indent stil-indent-offset))))
    (save-excursion
      (goto-char bol)
      (skip-chars-forward " \t")
      (when (looking-at "}")
        (cl-decf indent stil-indent-offset))
      (delete-region bol (point))
      (indent-to (max 0 indent)))
    (when (< (point) (current-indentation))
      (beginning-of-line-text))))

(defun stil-ts-indent-rules ()
  "Return tree-sitter indentation rules for STIL."
  (when (fboundp 'treesit-indent-rules)
    (treesit-simple-indent-rules
     'stil
     `((stil
        ((parent-is "source_file") parent-bol 0)
        ((node-is "}") parent-bol 0)
        ((parent-is "^[^{}]*{") parent-bol ,stil-indent-offset)
        ((parent-is ".") parent-bol 0))))))

;; ── Movement ────────────────────────────────────────────────────

(defconst stil--block-re
  (concat "^\\s-*" (regexp-opt
                    '("Header" "Signals" "SignalGroups" "ScanStructures"
                      "Spec" "Timing" "Selector" "PatternBurst" "PatternExec"
                      "Procedures" "MacroDefs" "Pattern" "Include"))
          "\\b"))

(defun stil-beginning-of-block ()
  "Move to the beginning of the current or previous top-level STIL block."
  (interactive)
  (let ((start (point)))
    (when (re-search-backward stil--block-re nil t)
      (when (= (point) start)
        (forward-line -1)
        (re-search-backward stil--block-re nil t)))))

(defun stil-end-of-block ()
  "Move to the end of the current or next top-level STIL block."
  (interactive)
  (let ((start (point)))
    (when (re-search-forward stil--block-re nil t)
      (goto-char (match-beginning 0))
      (backward-char 1)
      (skip-chars-backward " \t\n")
      (beginning-of-line)
      (when (<= (point) start)
        (forward-line 1)
        (when (re-search-forward stil--block-re nil t)
          (goto-char (match-beginning 0))
          (backward-char 1)
          (skip-chars-backward " \t\n")
          (beginning-of-line))))))

(defvar stil-mode-map
  (let ((map (make-sparse-keymap)))
    (define-key map [remap beginning-of-defun] #'stil-beginning-of-block)
    (define-key map [remap end-of-defun]       #'stil-end-of-block)
    map)
  "Keymap for STIL mode.")

;; ── Which-function ──────────────────────────────────────────────

(defun stil-which-function ()
  "Return the name of the STIL block containing point."
  (save-excursion
    (let ((pos (point))
          name)
      (goto-char (point-min))
      (while (and (re-search-forward stil--block-re pos t)
                  (not (eobp)))
        (let ((block-start (match-beginning 0))
              (block-name (or (match-string 1) "block")))
          (save-excursion
            (goto-char (match-end 0))
            (skip-chars-forward " \t")
            (when (looking-at "\\(?:\"[^\"]*\"\\|\\sw+\\)")
              (setq block-name (match-string 0)))
            (when (and (<= block-start pos)
                       (condition-case nil
                           (progn (forward-list) (>= (point) pos))
                         (error nil)))
              (setq name block-name)))))
      name)))

;; ── Flymake integration ─────────────────────────────────────────

(defcustom stil-lsp-server-command nil
  "Command to start the STIL language server.
When non-nil, eglot will use this command.  When nil, no LSP
integration is configured automatically."
  :type '(choice (const nil) (repeat string))
  :group 'stil)

(defcustom stil-use-flymake nil
  "When non-nil, use flymake to run the STIL parser/linter on save.
Ignored when `stil-lsp-server-command' is set."
  :type 'boolean
  :group 'stil)

(defun stil-flymake-lint (report-fn &rest _args)
  "Run the STIL parser/linter and report diagnostics via REPORT-FN."
  (let ((source (buffer-string))
        (file (buffer-file-name))
        (buffer (current-buffer))
        (proc (get-buffer-process " *stil-lint*")))
    (when (and proc (process-live-p proc))
      (kill-process proc))
    (let ((default-directory (or (when file (file-name-directory file))
                                  default-directory)))
      (setq proc
            (make-process
             :name "stil-lint"
             :buffer " *stil-lint*"
             :command (list "python3" "-c"
                            (concat
                             "import sys; "
                             "sys.path.insert(0, '"
                             (expand-file-name ".." (file-name-directory (or load-file-name "__FILE__")))
                             "'); "
                             "from parser.parse import parse; "
                             "from parser.lint import lint, Severity; "
                             "import json; "
                             "t = sys.stdin.read(); "
                             "r = parse(t); "
                             "diags = []; "
                             "errs = [{'line': max(e.line-1,0),'col': max(e.column-1,0),'msg': e.message} for e in r.errors] if not r.ok else []; "
                             "diags.extend(errs); "
                             "lr = lint(r.tree) if r.tree else None; "
                             "diags.extend([{'line': max(d.line-1,0),'col': d.column,'msg': d.message} for d in lr.diagnostics]) if lr else None; "
                             "print(json.dumps(diags))"))
             :sentinel
             (lambda (proc _event)
               (when (memq (process-status proc) '(exit signal))
                 (with-current-buffer buffer
                   (let ((diags nil)
                         (output (with-current-buffer (process-buffer proc)
                                   (goto-char (point-min))
                                   (buffer-substring (point) (point-max)))))
                     (dolist (d (condition-case nil (json-read-from-string output) (error nil)))
                       (push (flymake-make-diagnostic
                              buffer
                              (cons (alist-get 'line d) (alist-get 'col d))
                              (cons (alist-get 'line d) (1+ (alist-get 'col d)))
                              :error
                              (alist-get 'msg d))
                             diags))
                     (funcall report-fn diags))))))))
    (process-send-string proc source)
    (process-send-eof proc)))

;; ── LSP integration ─────────────────────────────────────────────

(with-eval-after-load 'eglot
  (add-to-list 'eglot-server-programs
               `(stil-mode . ,(or stil-lsp-server-command
                                  '("python3" "-m" "server.server")))))

;; ── Mode startup ────────────────────────────────────────────────

(defun stil--ts-available-p ()
  "Return non-nil if the tree-sitter STIL grammar is available."
  (and (fboundp 'treesit-ready-p)
       (treesit-ready-p 'stil t)))

(defun stil-mode-variables ()
  "Set up buffer-local variables for STIL mode."
  (setq-local comment-start "// ")
  (setq-local comment-end "")
  (setq-local comment-start-skip "//+\\s-*")
  (setq-local comment-multi-line nil)
  (setq-local block-comment-start "/*")
  (setq-local block-comment-end "*/")
  (setq-local indent-line-function #'stil-indent-line)
  (setq-local imenu-generic-expression stil-imenu-generic-expression)
  (setq-local font-lock-multiline t)
  (setq-local which-func-functions '(stil-which-function))
  (when (and stil-use-flymake (not stil-lsp-server-command))
    (add-hook 'flymake-diagnostic-functions #'stil-flymake-lint nil t)))

;;;###autoload
(define-derived-mode stil-mode prog-mode "STIL"
  "Major mode for editing IEEE Std 1450-1999 STIL files.

When the `tree-sitter-stil' grammar is available, uses tree-sitter
for font-lock and navigation.  Otherwise, uses regex-based font-lock.

\\{stil-mode-map}"
  (stil-mode-variables)

  (when (stil--ts-available-p)
    (treesit-parser-create 'stil)

    (setq-local treesit-font-lock-settings stil-ts-font-lock-rules)
    (setq-local treesit-font-lock-feature-list
                '((comment annotation)
                  (keyword type event)
                  (string constant name)))

    (setq-local imenu-create-index-function #'stil-ts-imenu-create-index)

    (treesit-major-mode-setup)

    (when (fboundp 'treesit-simple-indent-rules)
      (setq-local treesit-simple-indent-rules (stil-ts-indent-rules)))

    (treesit-font-lock-enable))

  (unless (stil--ts-available-p)
    (setq-local font-lock-defaults '(stil-font-lock-keywords nil t))))

;;;###autoload
(add-to-list 'auto-mode-alist '("\\.stil\\'" . stil-mode))

(provide 'stil-mode)

;;; stil-mode.el ends here
