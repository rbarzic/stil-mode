/**
 * @file Tree-sitter grammar for IEEE Std 1450-1999 STIL
 * (Standard Test Interface Language for Digital Test Vector Data)
 */

module.exports = grammar({
  name: "stil",

  extras: ($) => [/\s/, $.line_comment, $.block_comment],

  conflicts: ($) => [
    [$.sig_or_group, $._name_or_string],
    [$.wfc_tail, $._name_or_event],
  ],

  rules: {
    source_file: ($) => seq("STIL", $._float, ";", repeat($.top_level_block)),

    top_level_block: ($) =>
      choice(
        $.header_block,
        $.include_stmt,
        $.userkeywords_stmt,
        $.userfunctions_stmt,
        $.ann_stmt,
        $.signals_block,
        $.signalgroups_block,
        $.scanstructures_block,
        $.spec_block,
        $.selector_block,
        $.timing_block,
        $.patternburst_block,
        $.patternexec_block,
        $.procedures_block,
        $.macrodefs_block,
        $.pattern_block,
      ),

    _name_or_string: ($) => choice($.name, $.string),

    name: ($) => /[A-Za-z_][A-Za-z0-9_.]*/,

    string: ($) => token(seq('"', /[^"]*/, '"')),

    // ── Header ───────────────────────────────────────────────────

    header_block: ($) => seq("Header", "{", repeat($.header_item), "}"),

    header_item: ($) =>
      choice(
        seq("Title", $.string, ";"),
        seq("Date", $.string, ";"),
        seq("Source", $.string, ";"),
        seq("History", "{", repeat($.ann_stmt), "}"),
      ),

    // ── Include ──────────────────────────────────────────────────

    include_stmt: ($) => seq("Include", $.string, optional($.ifneed), ";"),
    ifneed: ($) => seq("IfNeed", $.name),

    // ── UserKeywords / UserFunctions ─────────────────────────────

    userkeywords_stmt: ($) => seq("UserKeywords", repeat1($.name), ";"),
    userfunctions_stmt: ($) => seq("UserFunctions", repeat1($.name), ";"),

    // ── Annotations ──────────────────────────────────────────────

    ann_stmt: ($) => seq("Ann", $.ann_body),
    ann_body: ($) => /\{\*[^*]*\*+(?:[^}*][^*]*\*+)*\}/,

    // ── Signals ──────────────────────────────────────────────────

    signals_block: ($) => seq("Signals", "{", repeat($.signal_def), "}"),

    signal_def: ($) =>
      choice(
        seq($._name_or_string, $.signal_dir, ";"),
        seq($._name_or_string, $.signal_dir, "{", repeat($.signal_attr), "}"),
      ),

    signal_dir: ($) => choice("In", "Out", "InOut", "Supply", "Pseudo"),

    signal_attr: ($) =>
      choice(
        seq("Termination", $.termination_type, ";"),
        seq("DefaultState", $.default_state, ";"),
        seq("Base", $.base_type, $.wfc_list, ";"),
        seq("Alignment", $.align_type, ";"),
        seq("ScanIn", optional(seq("(", $.integer, ")")), ";"),
        seq("ScanOut", optional(seq("(", $.integer, ")")), ";"),
        seq("DataBitCount", $.integer, ";"),
      ),

    termination_type: ($) =>
      choice("TerminateHigh", "TerminateLow", "TerminateOff", "TerminateUnknown"),

    default_state: ($) =>
      choice($.default_state_char, "ForceUp", "ForceDown", "ForceOff"),

    default_state_char: ($) => /[UDZ]/,

    base_type: ($) => choice("Hex", "Dec"),
    align_type: ($) => choice("MSB", "LSB"),

    // ── SignalGroups ─────────────────────────────────────────────

    signalgroups_block: ($) =>
      seq("SignalGroups", optional($._name_or_string), "{", repeat($.sg_def), "}"),

    sg_def: ($) =>
      choice(
        seq($._name_or_string, "=", $.sigref_expr, ";"),
        seq($._name_or_string, "=", $.sigref_expr, "{", repeat($.sg_attr), "}"),
      ),

    sg_attr: ($) =>
      choice(
        seq("Termination", $.termination_type, ";"),
        seq("DefaultState", $.default_state, ";"),
        seq("Base", $.base_type, $.wfc_list, ";"),
        seq("Alignment", $.align_type, ";"),
        seq("ScanIn", optional(choice(seq("(", $.integer, ")"), $.integer)), ";"),
        seq("ScanOut", optional(choice(seq("(", $.integer, ")"), $.integer)), ";"),
        seq("DataBitCount", $.integer, ";"),
      ),

    // ── ScanStructures ───────────────────────────────────────────

    scanstructures_block: ($) =>
      seq("ScanStructures", optional($._name_or_string), "{", repeat($.scanchain_def), "}"),

    scanchain_def: ($) =>
      seq("ScanChain", $._name_or_string, "{", repeat($.scanchain_item), "}"),

    scanchain_item: ($) =>
      choice(
        seq("ScanLength", $.integer, ";"),
        seq("ScanOutLength", $.integer, ";"),
        seq("ScanCells", repeat1(choice(token("!"), $.name)), ";"),
        seq("ScanIn", $._name_or_string, ";"),
        seq("ScanOut", $._name_or_string, ";"),
        seq("ScanMasterClock", repeat1($._name_or_string), ";"),
        seq("ScanSlaveClock", repeat1($._name_or_string), ";"),
        seq("ScanInversion", $.integer, ";"),
      ),

    // ── Spec ─────────────────────────────────────────────────────

    spec_block: ($) =>
      seq("Spec", optional($._name_or_string), "{", repeat1($.spec_entry), "}"),

    spec_entry: ($) =>
      choice(
        seq("Category", $._name_or_string, "{", repeat($.spec_var_def), "}"),
        seq("Variable", $._name_or_string, "{", repeat($.spec_cat_def), "}"),
      ),

    spec_var_def: ($) =>
      choice(
        seq($._name_or_string, "=", $.time_expr, ";"),
        seq($._name_or_string, "{", repeat($.spec_value_item), "}"),
      ),

    spec_cat_def: ($) =>
      choice(
        seq($._name_or_string, "=", $.time_expr, ";"),
        seq($._name_or_string, "{", repeat($.spec_value_item), "}"),
      ),

    spec_value_item: ($) =>
      choice(
        seq("Min", $.time_expr, ";"),
        seq("Typ", $.time_expr, ";"),
        seq("Max", $.time_expr, ";"),
        seq("Meas", $.time_expr, ";"),
      ),

    // ── Selector ─────────────────────────────────────────────────

    selector_block: ($) =>
      seq("Selector", $._name_or_string, "{", repeat($.selector_entry), "}"),

    selector_entry: ($) => seq($._name_or_string, $.selector_value, ";"),
    selector_value: ($) => choice("Min", "Typ", "Max", "Meas"),

    // ── Timing / WaveformTable ───────────────────────────────────

    timing_block: ($) =>
      seq("Timing", optional($._name_or_string), "{", repeat($.timing_item), "}"),

    timing_item: ($) =>
      choice(
        seq("SignalGroups", $._name_or_string, ";"),
        $.waveform_table,
      ),

    waveform_table: ($) =>
      seq("WaveformTable", $._name_or_string, "{", repeat($.wft_item), "}"),

    wft_item: ($) =>
      choice(
        seq("Period", $.time_expr, ";"),
        seq("InheritWaveformTable", $.dotted_name, ";"),
        $.subwaveforms_block,
        $.waveforms_block,
      ),

    dotted_name: ($) => seq($._name_or_string, repeat(seq(".", $._name_or_string))),

    // ── SubWaveforms ─────────────────────────────────────────────

    subwaveforms_block: ($) =>
      seq("SubWaveforms", "{", repeat($.subwf_def), "}"),

    subwf_def: ($) =>
      seq($._name_or_string, ":", "Duration", $.time_expr, "{", repeat($.subwf_event), "}"),

    subwf_event: ($) =>
      choice(
        seq($._name_or_string, ":", $.time_expr, $.event_or_list, ";"),
        seq($.time_expr, $.event_or_list, ";"),
      ),

    // ── Events ───────────────────────────────────────────────────

    event_or_list: ($) =>
      choice(
        seq($.event_name, repeat1(seq("/", $.event_name)), optional(seq("[", $.integer, "]"))),
        $.event_name,
      ),

    event_name: ($) =>
      choice(
        alias("ForceDown", $.keyword),
        alias("ForceUp", $.keyword),
        alias("ForceOff", $.keyword),
        alias("ForcePrior", $.keyword),
        alias("ForceUnknown", $.keyword),
        alias("CompareLow", $.keyword),
        alias("CompareHigh", $.keyword),
        alias("CompareUnknown", $.keyword),
        alias("CompareOff", $.keyword),
        alias("CompareValid", $.keyword),
        alias("CompareLowWindow", $.keyword),
        alias("CompareHighWindow", $.keyword),
        alias("CompareOffWindow", $.keyword),
        alias("CompareValidWindow", $.keyword),
        alias("ExpectLow", $.keyword),
        alias("ExpectHigh", $.keyword),
        alias("ExpectOff", $.keyword),
        alias("Marker", $.keyword),
        alias("LogicLow", $.keyword),
        alias("LogicHigh", $.keyword),
        alias("LogicZ", $.keyword),
        alias("Unknown", $.keyword),
        $.event_char,
      ),

    event_char: ($) => /[DPUZNLTVMABFRGHQ?lhtv]/,

    // ── Waveforms ────────────────────────────────────────────────

    waveforms_block: ($) =>
      seq("Waveforms", "{", repeat($.waveform_entry), "}"),

    waveform_entry: ($) =>
      seq($.sig_or_group, "{", repeat($.wf_char_def), "}"),

    sig_or_group: ($) => choice($._name_or_string, $.sigref_expr),

    wf_char_def: ($) =>
      choice(
        seq("InheritWaveform", $.dotted_name, ";"),
        $.wfc_block,
      ),

    wfc_block: ($) =>
      seq($.wfc_label, "{", repeat($.wfc_inner_item), "}"),

    wfc_label: ($) => /[A-Za-z0-9]+/,

    wfc_inner_item: ($) =>
      choice(
        seq("InheritWaveform", $.dotted_name, ";"),
        seq($._name_or_string, ":", $.time_expr, optional($.repeat_op), $.wfc_tail, ";"),
        seq($.time_expr, optional($.repeat_op), $.wfc_tail, ";"),
      ),

    wfc_tail: ($) =>
      choice(
        seq($._name_or_event, repeat1(seq("/", $._name_or_event)), optional(seq("[", $.integer, "]"))),
        seq($._name_or_event, optional(seq("[", $.integer, "]"))),
        $._name_or_string,
      ),

    _name_or_event: ($) => choice($._name_or_string, $.event_char),

    // ── PatternBurst ─────────────────────────────────────────────

    patternburst_block: ($) =>
      seq("PatternBurst", $._name_or_string, "{", repeat($.pb_item), "}"),

    pb_item: ($) =>
      choice(
        seq("SignalGroups", $._name_or_string, ";"),
        seq("MacroDefs", $._name_or_string, ";"),
        seq("Procedures", $._name_or_string, ";"),
        seq("ScanStructures", optional($._name_or_string), ";"),
        seq("Start", $._name_or_string, ";"),
        seq("Stop", $._name_or_string, ";"),
        $.pb_termination,
        $.patlist_block,
      ),

    pb_termination: ($) => seq("Termination", "{", repeat($.term_entry), "}"),
    term_entry: ($) => seq($.sig_or_group, $.termination_type, ";"),

    patlist_block: ($) =>
      seq("PatList", "{", repeat($.patlist_entry), "}"),

    patlist_entry: ($) =>
      choice(
        seq($._name_or_string, ";"),
        seq($._name_or_string, "{", repeat($.pb_item), "}"),
      ),

    // ── PatternExec ──────────────────────────────────────────────

    patternexec_block: ($) =>
      seq("PatternExec", optional($._name_or_string), "{", repeat($.pe_item), "}"),

    pe_item: ($) =>
      choice(
        seq("Category", $._name_or_string, ";"),
        seq("Selector", $._name_or_string, ";"),
        seq("Timing", $._name_or_string, ";"),
        seq("PatternBurst", $._name_or_string, ";"),
      ),

    // ── Procedures / MacroDefs ───────────────────────────────────

    procedures_block: ($) =>
      seq("Procedures", optional($._name_or_string), "{", repeat($.proc_def), "}"),

    proc_def: ($) =>
      seq($._name_or_string, "{", repeat($.pattern_stmt), "}"),

    macrodefs_block: ($) =>
      seq("MacroDefs", optional($._name_or_string), "{", repeat($.macro_def), "}"),

    macro_def: ($) =>
      seq($._name_or_string, "{", repeat($.pattern_stmt), "}"),

    // ── Pattern ──────────────────────────────────────────────────

    pattern_block: ($) =>
      seq("Pattern", $._name_or_string, "{", repeat($.pattern_body), "}"),

    pattern_body: ($) =>
      choice(
        seq("TimeUnit", $.time_expr, ";"),
        $.pattern_stmt,
      ),

    // ── Pattern statements ───────────────────────────────────────

    pattern_stmt: ($) =>
      choice(
        $.labeled_stmt,
        $.vector_stmt,
        $.condition_stmt,
        $.wft_stmt,
        $.call_stmt,
        $.macro_stmt,
        $.loop_stmt,
        $.matchloop_stmt,
        $.goto_stmt,
        $.breakpoint_stmt,
        $.iddq_stmt,
        $.stop_stmt,
        $.scanchain_stmt,
        $.shift_stmt,
        $.ann_stmt,
      ),

    labeled_stmt: ($) =>
      seq(
        $._name_or_string,
        ":",
        choice(
          $.vector_stmt,
          $.condition_stmt,
          $.wft_stmt,
          $.call_stmt,
          $.macro_stmt,
          $.loop_stmt,
          $.matchloop_stmt,
          $.goto_stmt,
          $.breakpoint_stmt,
          $.iddq_stmt,
          $.stop_stmt,
          $.scanchain_stmt,
          $.shift_stmt,
          $.ann_stmt,
        ),
      ),

    vector_stmt: ($) =>
      choice(
        seq("Vector", "{", repeat($.vec_data_item), "}"),
        seq("V", "{", repeat($.vec_data_item), "}"),
      ),

    condition_stmt: ($) =>
      choice(
        seq("Condition", "{", repeat($.vec_data_item), "}"),
        seq("C", "{", repeat($.vec_data_item), "}"),
      ),

    wft_stmt: ($) =>
      choice(
        seq("WaveformTable", $._name_or_string, ";"),
        seq("W", $._name_or_string, ";"),
      ),

    call_stmt: ($) =>
      choice(
        seq("Call", $._name_or_string, ";"),
        seq("Call", $._name_or_string, "{", repeat($.call_data_item), "}"),
      ),

    macro_stmt: ($) =>
      choice(
        seq("Macro", $._name_or_string, ";"),
        seq("Macro", $._name_or_string, "{", repeat($.call_data_item), "}"),
      ),

    loop_stmt: ($) =>
      seq("Loop", $.integer, "{", repeat($.pattern_stmt), "}"),

    matchloop_stmt: ($) =>
      seq("MatchLoop", $.match_loop_count, "{", repeat1($.pattern_stmt), $.breakpoint_block, "}"),

    match_loop_count: ($) => choice($.integer, "Infinite"),
    breakpoint_block: ($) => seq("BreakPoint", "{", repeat1($.pattern_stmt), "}"),
    goto_stmt: ($) => seq("Goto", $._name_or_string, ";"),

    breakpoint_stmt: ($) =>
      choice(seq("BreakPoint", ";"), seq("BreakPoint", "{", repeat($.pattern_stmt), "}")),

    iddq_stmt: ($) => seq("IDDQ", "TestPoint", ";"),
    stop_stmt: ($) => seq("Stop", ";"),
    scanchain_stmt: ($) => seq("ScanChain", $._name_or_string, ";"),
    shift_stmt: ($) => seq("Shift", "{", repeat1($.pattern_stmt), "}"),

    // ── Vector data ──────────────────────────────────────────────

    vec_data_item: ($) =>
      choice(
        seq($.sig_or_group, "=", $.vec_data, ";"),
        seq($.sig_or_group, "{", $.vec_data, ";", "}"),
        $.noncyclized_data,
      ),

    noncyclized_data: ($) =>
      choice(
        seq("@", $.integer, $.sig_or_group, "=", $.event_or_list, ";"),
        seq("@", $.integer, "{", repeat1($.nc_item), "}"),
      ),

    nc_item: ($) => seq($.sig_or_group, "=", $.event_or_list, ";"),
    call_data_item: ($) => seq($.sig_or_group, "=", $.vec_data, ";"),
    vec_data: ($) => repeat1($.vec_data_chunk),

    vec_data_chunk: ($) =>
      choice(
        $.repeat_op,
        /\\h[a-zA-Z0-9]*/,
        /\\d[a-zA-Z0-9]*/,
        /\\l[0-9]*/,
        /\\w/,
        /[0-9A-Za-z#%]+/,
      ),

    // ── Terminals ────────────────────────────────────────────────

    sigref_expr: ($) => /'[^']*'/,
    time_expr: ($) => /'[^']*'/,
    wfc_list: ($) => /[A-Za-z0-9]{2,}/,
    repeat_op: ($) => /\\r[0-9]+/,
    _float: ($) => /[0-9]+\.[0-9]+/,
    integer: ($) => /[0-9]+/,
    line_comment: ($) => /\/\/[^\n]*/,
    block_comment: ($) => /\/\*[\s\S]*?\*\//,
  },
});
