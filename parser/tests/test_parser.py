import pytest
from pathlib import Path

EXAMPLES = Path(__file__).parent.parent.parent / "examples"


@pytest.fixture(autouse=True)
def reset_parser():
    import parser.parse

    parser.parse._PARSER = None


def _parse(text):
    from parser.parse import parse

    return parse(text)


def _parse_ok(text):
    result = _parse(text)
    assert result.ok, f"Parse failed: {result.errors}"
    return result


def _lint(tree):
    from parser.lint import lint

    return lint(tree)


# ── Minimal valid file ──────────────────────────────────────────


class TestMinimal:
    def test_empty_file(self):
        r = _parse_ok("STIL 1.0;")
        toplvl_count = sum(
            1 for c in r.tree.children if hasattr(c, "data") and c.data == "toplvl"
        )
        assert toplvl_count == 0

    def test_stil_version(self):
        r = _parse_ok("STIL 1.0;")
        assert r.tree.data == "start"

    def test_bad_version(self):
        r = _parse("STIL xyz;")
        assert not r.ok


# ── Header ──────────────────────────────────────────────────────


class TestHeader:
    def test_header(self):
        r = _parse_ok('STIL 1.0; Header { Title "test"; }')
        toplvls = [
            c for c in r.tree.children if hasattr(c, "data") and c.data == "toplvl"
        ]
        tl = toplvls[0].children[0]
        assert tl.data == "header_block"

    def test_header_with_history(self):
        r = _parse_ok("STIL 1.0; Header { History { Ann {* created *} } }")


# ── Signals ─────────────────────────────────────────────────────


class TestSignals:
    def test_simple_signals(self):
        r = _parse_ok("STIL 1.0; Signals { clk In; data Out; }")
        toplvls = [
            c for c in r.tree.children if hasattr(c, "data") and c.data == "toplvl"
        ]
        tl = toplvls[0].children[0]
        assert tl.data == "signals_block"
        assert len(tl.children) == 2

    def test_signal_with_scanin(self):
        r = _parse_ok("STIL 1.0; Signals { si In { ScanIn; } }")

    def test_signal_with_scanin_length(self):
        r = _parse_ok("STIL 1.0; Signals { si In { ScanIn(100); } }")

    def test_signal_quoted_name(self):
        r = _parse_ok('STIL 1.0; Signals { "my sig" InOut; }')

    def test_all_directions(self):
        r = _parse_ok("STIL 1.0; Signals { a In; b Out; c InOut; d Supply; e Pseudo; }")


# ── SignalGroups ────────────────────────────────────────────────


class TestSignalGroups:
    def test_basic_groups(self):
        r = _parse_ok("STIL 1.0; Signals { a In; b In; } SignalGroups { g1 = 'a+b'; }")

    def test_empty_group(self):
        r = _parse_ok("STIL 1.0; Signals { a In; } SignalGroups { empty = ''; }")

    def test_group_with_attrs(self):
        r = _parse_ok(
            "STIL 1.0; Signals { a In; b In; } SignalGroups { g = 'a+b' { ScanIn 10; } }"
        )


# ── Timing ──────────────────────────────────────────────────────


class TestTiming:
    def test_basic_timing(self):
        src = """STIL 1.0;
        Signals { clk In; }
        Timing {
            WaveformTable wft1 {
                Period '100ns';
                Waveforms {
                    clk { P { '0ns' D; '50ns' U; '80ns' D; } }
                }
            }
        }"""
        r = _parse_ok(src)

    def test_event_list(self):
        src = """STIL 1.0;
        Signals { a InOut; }
        Timing {
            WaveformTable wft {
                Period '40ns';
                Waveforms {
                    a { 01 { '0ns' D/U; } }
                }
            }
        }"""
        r = _parse_ok(src)


# ── Spec / Selector ────────────────────────────────────────────


class TestSpec:
    def test_spec_category(self):
        src = """STIL 1.0;
        Spec s1 {
            Category fast {
                t1 = '50ns';
            }
        }"""
        r = _parse_ok(src)

    def test_spec_min_typ_max(self):
        src = """STIL 1.0;
        Spec s1 {
            Category slow {
                t1 { Min '30ns'; Typ '50ns'; Max '70ns'; }
            }
        }"""
        r = _parse_ok(src)

    def test_selector(self):
        src = """STIL 1.0;
        Selector typ_sel {
            t1 Typ;
        }"""
        r = _parse_ok(src)


# ── Pattern / PatternBurst / PatternExec ───────────────────────


class TestPattern:
    def test_simple_pattern(self):
        src = """STIL 1.0;
        Signals { a In; b Out; }
        SignalGroups { all = 'a+b'; }
        Timing { WaveformTable wft { Period '100ns'; Waveforms { a { 0 { '0ns' D; } } } } }
        PatternBurst main { PatList { p1; } }
        PatternExec { PatternBurst main; }
        Pattern p1 {
            W wft;
            V { all = 0X; }
        }"""
        r = _parse_ok(src)

    def test_labeled_vector(self):
        src = """STIL 1.0;
        Pattern p1 {
            W wft;
            LABEL1: V { a = 0; }
        }"""
        r = _parse_ok(src)

    def test_condition_stmt(self):
        src = """STIL 1.0;
        Pattern p1 {
            C { a = 0; }
        }"""
        r = _parse_ok(src)

    def test_loop(self):
        src = """STIL 1.0;
        Pattern p1 {
            Loop 10 { V { a = 0; } }
        }"""
        r = _parse_ok(src)

    def test_goto(self):
        src = """STIL 1.0;
        Pattern p1 {
            LOOP: V {}
            Goto LOOP;
        }"""
        r = _parse_ok(src)

    def test_stop(self):
        src = """STIL 1.0;
        Pattern p1 {
            Stop;
        }"""
        r = _parse_ok(src)

    def test_macro_and_call(self):
        src = """STIL 1.0;
        Procedures { proc1 { V { a = 0; } } }
        MacroDefs { mac1 { V { a = 1; } } }
        Pattern p1 {
            Macro mac1;
            Call proc1 { a = 0101; }
            Macro mac1 { a = HHHH; }
        }"""
        r = _parse_ok(src)


# ── Annotations ────────────────────────────────────────────────


class TestAnnotations:
    def test_ann_top_level(self):
        r = _parse_ok("STIL 1.0; Ann {* this is a note *}")

    def test_ann_in_pattern(self):
        src = """STIL 1.0;
        Pattern p1 {
            Ann {* step 1 *}
            V { a = 0; }
        }"""
        r = _parse_ok(src)


# ── Comments ───────────────────────────────────────────────────


class TestComments:
    def test_line_comment(self):
        r = _parse_ok("STIL 1.0; // this is a comment\n Signals { a In; }")

    def test_block_comment(self):
        r = _parse_ok("STIL 1.0; /* block */ Signals { a In; }")


# ── Lint checks ────────────────────────────────────────────────


class TestLint:
    def test_clean(self):
        r = _parse_ok("STIL 1.0; Signals { a In; b Out; }")
        lr = _lint(r.tree)
        assert lr.ok
        assert len(lr.diagnostics) == 0

    def test_block_ordering_warning(self):
        src = """STIL 1.0;
        Signals { a In; }
        Pattern p1 { }
        Timing { }
        """
        r = _parse_ok(src)
        lr = _lint(r.tree)
        assert any("ordering" in d.message for d in lr.diagnostics)

    def test_duplicate_signals(self):
        src = """STIL 1.0;
        Signals { a In; a Out; }
        """
        r = _parse_ok(src)
        lr = _lint(r.tree)
        assert any("Duplicate signal" in d.message for d in lr.diagnostics)

    def test_duplicate_patterns(self):
        src = """STIL 1.0;
        Pattern p1 { }
        Pattern p1 { }
        """
        r = _parse_ok(src)
        lr = _lint(r.tree)
        assert any("Duplicate pattern" in d.message for d in lr.diagnostics)


# ── Integration tests (real files) ─────────────────────────────


class TestIntegration:
    @pytest.mark.parametrize(
        "path",
        [
            "example1.stil",
            "STIL.ELASTIC.chip_compression.signals.stil",
            "STIL.ELASTIC.chip_compression.scan.ex1.ts1.stil",
            "STIL.ELASTIC.chip_compression.logic.ex1.ts2.stil",
        ],
    )
    def test_parse_example(self, path):
        from parser.parse import parse_file

        result = parse_file(EXAMPLES / path)
        assert result.ok, f"Parse failed for {path}: {result.errors}"

    @pytest.mark.parametrize(
        "path",
        [
            "example1.stil",
            "STIL.ELASTIC.chip_compression.signals.stil",
            "STIL.ELASTIC.chip_compression.scan.ex1.ts1.stil",
            "STIL.ELASTIC.chip_compression.logic.ex1.ts2.stil",
        ],
    )
    def test_lint_example(self, path):
        from parser.parse import parse_file

        result = parse_file(EXAMPLES / path)
        assert result.ok
        lr = _lint(result.tree)
        assert lr.ok, f"Lint errors for {path}: {lr.errors}"
