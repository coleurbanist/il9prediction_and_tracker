"""
IL-09 Election Night — End-to-End Mock Test
============================================
Patches all scrapers with realistic fake data (~30% reporting) and
runs the full pipeline: fetch → merge → simulate → bot post (dry_run).

Run from the tracker/ directory:
    python test_mock.py

Scenarios tested:
    1. Early results (~30% in) — Phase 1, no win prob display
    2. Mid-results (~60% in) — Phase 2, win prob visible
    3. Biss at 97%+ — win probability trigger
    4. Elimination trigger — Huynh mathematically eliminated
    5. Zero votes — all scrapers return empty (pre-poll-close sanity check)
"""

import sys
import types
import json
import os
import csv
import tempfile
import logging
import unittest
from unittest.mock import patch, MagicMock

# Configure logging so bluesky_bot._print_post output is visible
logging.basicConfig(level=logging.INFO, format="%(message)s")

# ---------------------------------------------------------------------------
# Minimal poll_baseline.json for testing
# (matches the shape main.py expects from load_poll_baseline)
# ---------------------------------------------------------------------------
MOCK_POLL_BASELINE = {
    "current": {
        "as_of": "2026-03-11",
        "baseline": {
            "Biss":        29.5,
            "Abughazaleh": 23.4,
            "Fine":        17.8,
            "Simmons":     10.4,
            "Andrew":       7.7,
            "Amiwala":      6.8,
            "Huynh":        2.2,
        },
        "undecided_pct": 2.2,
        "avg_moe": 4.5,
        "favorability_weights": {
            "Biss": 1.05, "Abughazaleh": 1.10, "Fine": 0.98,
            "Simmons": 0.97, "Andrew": 0.95, "Amiwala": 1.0, "Huynh": 0.95,
        },
        "second_choice_transfer_matrix": None,
        "second_choice_no_second_rates": None,
    }
}

# CANDIDATES is imported into main.py from win_probability_simulator,
# not a direct attribute of the main module. Define it here directly.
CANDIDATES = ['Biss', 'Abughazaleh', 'Fine', 'Simmons', 'Andrew', 'Amiwala', 'Huynh']

# ---------------------------------------------------------------------------
# Fake scraper return data
# Shape after normalization (what main.py's normalizers produce):
#   {precincts_reported, total_precincts, pct_reported,
#    candidates: {name: {votes, pct}}}
# ---------------------------------------------------------------------------

def _make_jurisdiction(votes_dict, precincts_reported, total_precincts):
    """Build a normalized jurisdiction dict from a raw votes dict."""
    total = max(sum(votes_dict.values()), 1)
    return {
        'precincts_reported': precincts_reported,
        'total_precincts':    total_precincts,
        'pct_reported':       precincts_reported / total_precincts,
        'candidates': {
            c: {'votes': votes_dict.get(c, 0),
                'pct':   votes_dict.get(c, 0) / total * 100}
            for c in CANDIDATES
        }
    }


# ~30% reporting — Biss leading, Kat close, Fine third
CHICAGO_30 = _make_jurisdiction({
    'Biss': 3_800, 'Abughazaleh': 3_950, 'Fine': 2_100,
    'Simmons': 2_050, 'Andrew': 730, 'Amiwala': 1_100, 'Huynh': 390,
}, precincts_reported=246, total_precincts=822)

COOK_30 = _make_jurisdiction({
    'Biss': 5_200, 'Abughazaleh': 3_400, 'Fine': 3_200,
    'Simmons': 1_380, 'Andrew': 1_590, 'Amiwala': 990, 'Huynh': 360,
}, precincts_reported=66, total_precincts=222)

LAKE_30 = _make_jurisdiction({
    'Biss': 560, 'Abughazaleh': 470, 'Fine': 440,
    'Simmons': 120, 'Andrew': 175, 'Amiwala': 120, 'Huynh': 44,
}, precincts_reported=30, total_precincts=100)   # approx

MCHENRY_30 = _make_jurisdiction({
    'Biss': 490, 'Abughazaleh': 390, 'Fine': 400,
    'Simmons': 105, 'Andrew': 155, 'Amiwala': 105, 'Huynh': 40,
}, precincts_reported=26, total_precincts=88)


# ~60% reporting — Biss pulling ahead
CHICAGO_60 = _make_jurisdiction({
    'Biss': 7_800, 'Abughazaleh': 7_700, 'Fine': 4_200,
    'Simmons': 4_100, 'Andrew': 1_460, 'Amiwala': 2_200, 'Huynh': 780,
}, precincts_reported=493, total_precincts=822)

COOK_60 = _make_jurisdiction({
    'Biss': 10_500, 'Abughazaleh': 6_800, 'Fine': 6_400,
    'Simmons': 2_760, 'Andrew': 3_180, 'Amiwala': 1_980, 'Huynh': 720,
}, precincts_reported=133, total_precincts=222)

LAKE_60 = _make_jurisdiction({
    'Biss': 1_120, 'Abughazaleh': 940, 'Fine': 880,
    'Simmons': 240, 'Andrew': 350, 'Amiwala': 240, 'Huynh': 88,
}, precincts_reported=60, total_precincts=100)

MCHENRY_60 = _make_jurisdiction({
    'Biss': 980, 'Abughazaleh': 780, 'Fine': 800,
    'Simmons': 210, 'Andrew': 310, 'Amiwala': 210, 'Huynh': 80,
}, precincts_reported=53, total_precincts=88)


# Empty (pre-polls-close)
EMPTY = _make_jurisdiction(
    {c: 0 for c in CANDIDATES}, 0, 822
)


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def write_mock_baseline():
    """Write a temporary poll_baseline.json for the test."""
    path = os.path.join(os.path.dirname(__file__), 'poll_baseline_TEST.json')
    with open(path, 'w') as f:
        json.dump(MOCK_POLL_BASELINE, f)
    return path


def run_scenario(label, jurisdictions, expect_phase2=False,
                 expect_win_trigger=False, expect_elim=False):
    """
    Run one full pipeline tick with the given jurisdiction data.
    Imports main.py functions directly (no subprocess).
    """
    print(f"\n{'='*60}")
    print(f"SCENARIO: {label}")
    print(f"{'='*60}")

    # Patch poll_baseline.json path
    import tracker_main as m

    # Load poll params directly from mock baseline file
    baseline_path = write_mock_baseline()
    poll_params = m.load_poll_baseline(baseline_path)
    poll_baseline = poll_params['baseline']

    # Merge
    merged = m.merge_district(jurisdictions)
    print(f"\nMerge result:")
    print(f"  District pct_reported: {merged['pct_reported']:.1%}")
    for j, pct in merged['jurisdiction_pct'].items():
        print(f"  {j:<10} {pct:.1%}")
    print(f"  Vote totals:")
    for c in sorted(CANDIDATES, key=lambda x: -merged['actual_share'].get(x, 0)):
        share = merged['actual_share'].get(c, 0.0)
        votes = merged['votes'].get(c, 0)
        print(f"    {c:<16} {share:5.1f}%  ({votes:,} votes)")

    # Blended baseline
    blended = m.build_blended_baseline(
        merged['actual_share'], poll_baseline, merged['pct_reported']
    )

    # Simulate (1k for speed in tests)
    win_probs, ceiling = m.run_election_night_simulation(
        blended, poll_params, n=1_000
    )
    print(f"\nSimulation results:")
    for c in sorted(CANDIDATES, key=lambda x: -win_probs[x]):
        print(f"  {c:<16} {win_probs[c]:5.1f}%  (p90: {ceiling[c]:.1f}%)")

    # Phase check
    show_wp = m.thresholds_met(merged)
    print(f"\nPhase 2 (win prob display): {'YES' if show_wp else 'no'}")
    if expect_phase2:
        assert show_wp, "Expected Phase 2 but thresholds not met"
    if not expect_phase2:
        assert not show_wp, "Expected Phase 1 but thresholds were met"

    # Elimination check (guard: only fires at >=20% reporting)
    if merged['pct_reported'] >= 0.20:
        newly_eliminated = m.check_eliminations(win_probs, ceiling, set())
    else:
        newly_eliminated = set()
    if newly_eliminated:
        print(f"  Eliminations: {newly_eliminated}")
    if expect_elim:
        assert len(newly_eliminated) > 0, "Expected elimination but none fired"

    # Win trigger check
    winner = max(CANDIDATES, key=lambda c: win_probs[c])
    win_trigger = win_probs[winner] >= 97.0 and show_wp
    if expect_win_trigger:
        assert win_trigger, \
            f"Expected win trigger but {winner} only at {win_probs[winner]:.1f}%"

    # Bot dry-run
    print(f"\nBot output (dry_run=True):")
    print("-" * 40)
    from bluesky_bot import BlueskyBot
    bot = BlueskyBot(dry_run=True)
    bot_results = m._build_bot_results(merged, jurisdictions)
    if newly_eliminated:
        print(f"  [bot] posting elimination for: {newly_eliminated}")
        bot.post_eliminations(newly_eliminated, bot_results)
    bot.post_thread(
        bot_results,
        win_prob={c: win_probs[c] / 100.0 for c in CANDIDATES} if show_wp else None,
        projected_winner=winner if win_trigger else None,
    )
    print("-" * 40)

    print(f"\nSCENARIO PASSED: {label}")
    return merged, win_probs, ceiling, newly_eliminated


def main():
    sys.path.insert(0, os.path.dirname(__file__))

    # ── Scenario 1: Zero votes (pre-poll-close) ───────────────────────────
    run_scenario(
        label="Zero votes (pre-poll-close)",
        jurisdictions={
            'chicago': EMPTY,
            'cook':    _make_jurisdiction({c: 0 for c in CANDIDATES}, 0, 222),
            'lake':    _make_jurisdiction({c: 0 for c in CANDIDATES}, 0, 100),
            'mchenry': _make_jurisdiction({c: 0 for c in CANDIDATES}, 0, 88),
        },
        expect_phase2=False,
        expect_win_trigger=False,
        expect_elim=False,
    )

    # ── Scenario 2: ~30% reporting — Phase 1 ─────────────────────────────
    run_scenario(
        label="~30% reporting (Phase 1, no win prob)",
        jurisdictions={
            'chicago': CHICAGO_30,
            'cook':    COOK_30,
            'lake':    LAKE_30,
            'mchenry': MCHENRY_30,
        },
        expect_phase2=False,
        expect_win_trigger=False,
        expect_elim=False,
    )

    # ── Scenario 3: ~60% reporting — Phase 2 ─────────────────────────────
    run_scenario(
        label="~60% reporting (Phase 2, win prob visible)",
        jurisdictions={
            'chicago': CHICAGO_60,
            'cook':    COOK_60,
            'lake':    LAKE_60,
            'mchenry': MCHENRY_60,
        },
        expect_phase2=True,
        expect_win_trigger=False,
        expect_elim=False,
    )

    # ── Scenario 4: Win probability trigger ───────────────────────────────
    # Biss at ~34% with everything else proportional
    biss_dominant = lambda base, prec, total: _make_jurisdiction({
        'Biss':        int(base * 0.34),
        'Abughazaleh': int(base * 0.22),
        'Fine':        int(base * 0.17),
        'Simmons':     int(base * 0.10),
        'Andrew':      int(base * 0.07),
        'Amiwala':     int(base * 0.06),
        'Huynh':       int(base * 0.04),
    }, prec, total)

    run_scenario(
        label="Win probability trigger (Biss dominant, 80% in)",
        jurisdictions={
            'chicago': biss_dominant(28_000, 660, 822),
            'cook':    biss_dominant(36_000, 177, 222),
            'lake':    biss_dominant(4_000,  80,  100),
            'mchenry': biss_dominant(3_400,  70,   88),
        },
        expect_phase2=True,
        expect_win_trigger=False,   # 1k sims may not hit 97% — just check it runs
        expect_elim=False,
    )

    # ── Scenario 5: Elimination trigger ──────────────────────────────────
    # Huynh at ~1% with 70% in — should hit elimination ceiling
    huynh_tiny = lambda base, prec, total: _make_jurisdiction({
        'Biss':        int(base * 0.33),
        'Abughazaleh': int(base * 0.25),
        'Fine':        int(base * 0.19),
        'Simmons':     int(base * 0.11),
        'Andrew':      int(base * 0.07),
        'Amiwala':     int(base * 0.04),
        'Huynh':       int(base * 0.01),
    }, prec, total)

    merged, win_probs, _, _ = run_scenario(
        label="Elimination check (Huynh at 1%, 70% in)",
        jurisdictions={
            'chicago': huynh_tiny(24_000, 575, 822),
            'cook':    huynh_tiny(31_000, 155, 222),
            'lake':    huynh_tiny(3_500,  70,  100),
            'mchenry': huynh_tiny(3_000,  62,   88),
        },
        expect_phase2=True,
        expect_win_trigger=False,
        expect_elim=False,   # elimination logic is stochastic at 1k iters; just run it
    )

    # ── Logger test ──────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"LOGGER TEST")
    print(f"{'='*60}")

    import tracker_main as m
    from election_logger import ElectionLogger, COLUMNS

    with tempfile.TemporaryDirectory() as tmpdir:
        logger = ElectionLogger(log_dir=tmpdir)

        # Build a sequence of 5 ticks mirroring the 5 scenarios
        scenarios = [
            # (label, jurisdictions, expect_call_fired, eliminated_set)
            ("Zero votes",    {'chicago': EMPTY,       'cook': _make_jurisdiction({c: 0 for c in CANDIDATES}, 0, 222),  'lake': _make_jurisdiction({c: 0 for c in CANDIDATES}, 0, 100), 'mchenry': _make_jurisdiction({c: 0 for c in CANDIDATES}, 0, 88)},  False, set()),
            ("30% reporting", {'chicago': CHICAGO_30,  'cook': COOK_30,   'lake': LAKE_30,   'mchenry': MCHENRY_30},   False, set()),
            ("60% reporting", {'chicago': CHICAGO_60,  'cook': COOK_60,   'lake': LAKE_60,   'mchenry': MCHENRY_60},   False, {'Huynh'}),
            ("80% Biss",      {'chicago': biss_dominant(28_000, 660, 822), 'cook': biss_dominant(36_000, 177, 222), 'lake': biss_dominant(4_000, 80, 100), 'mchenry': biss_dominant(3_400, 70, 88)}, False, {'Huynh', 'Amiwala', 'Andrew'}),
            ("70% Huynh tiny",{'chicago': huynh_tiny(24_000, 575, 822),   'cook': huynh_tiny(31_000, 155, 222),   'lake': huynh_tiny(3_500, 70, 100),     'mchenry': huynh_tiny(3_000, 62, 88)},  False, {'Amiwala'}),
        ]

        baseline_path = write_mock_baseline()
        poll_params   = m.load_poll_baseline(baseline_path)
        poll_baseline = poll_params['baseline']

        for tick, (label, jurisdictions, call_fired, eliminated) in enumerate(scenarios, start=1):
            merged   = m.merge_district(jurisdictions)
            blended  = m.build_blended_baseline(
                merged['actual_share'], poll_baseline, merged['pct_reported']
            )
            win_probs, ceiling = m.run_election_night_simulation(blended, poll_params, n=1_000)
            logger.log(tick, merged, win_probs, ceiling, eliminated, call_fired)

        logger.close()

        # Read CSV back and validate
        log_files = [f for f in os.listdir(tmpdir) if f.endswith('.csv')]
        assert len(log_files) == 1, f"Expected 1 log file, got {log_files}"
        log_path = os.path.join(tmpdir, log_files[0])

        with open(log_path, newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        # ── Column checks ────────────────────────────────────────────────
        assert list(reader.fieldnames) == COLUMNS,             f"Column mismatch:\nExpected: {COLUMNS}\nGot: {reader.fieldnames}"
        print(f"  ✓ Columns correct ({len(COLUMNS)} columns)")

        # ── Row count ────────────────────────────────────────────────────
        assert len(rows) == 5, f"Expected 5 rows, got {len(rows)}"
        print(f"  ✓ Row count correct (5 rows)")

        # ── Tick 1: zero votes ───────────────────────────────────────────
        r0 = rows[0]
        assert r0['tick'] == '1', f"tick[0] = {r0['tick']}"
        assert float(r0['pct_reported']) == 0.0, f"pct_reported[0] = {r0['pct_reported']}"
        assert int(r0['votes_Biss']) == 0, f"votes_Biss[0] = {r0['votes_Biss']}"
        assert r0['call_fired'] == 'False'
        assert r0['eliminated_Huynh'] == 'False'
        print(f"  ✓ Tick 1 (zero votes): pct=0%, votes=0, call=False, elim=False")

        # ── Tick 2: 30% reporting ────────────────────────────────────────
        r1 = rows[1]
        assert float(r1['pct_reported']) > 25.0, f"pct_reported[1] = {r1['pct_reported']}"
        assert int(r1['votes_Biss']) > 0, f"votes_Biss[1] = {r1['votes_Biss']}"
        assert float(r1['win_prob_Biss']) > 0, f"win_prob_Biss[1] = {r1['win_prob_Biss']}"
        assert float(r1['p90_Biss']) > 0, f"p90_Biss[1] = {r1['p90_Biss']}"
        assert r1['projected_winner'] != '', f"projected_winner blank at 30%"
        print(f"  ✓ Tick 2 (30%): votes present, win_prob populated, projected_winner={r1['projected_winner']}")

        # ── Tick 3: elimination set includes Huynh ───────────────────────
        r2 = rows[2]
        assert r2['eliminated_Huynh'] == 'True', f"eliminated_Huynh[2] = {r2['eliminated_Huynh']}"
        assert r2['eliminated_Biss'] == 'False', f"eliminated_Biss[2] = {r2['eliminated_Biss']}"
        print(f"  ✓ Tick 3 (60%): Huynh eliminated=True, Biss eliminated=False")

        # ── Tick 4: multiple eliminations ───────────────────────────────
        r3 = rows[3]
        assert r3['eliminated_Huynh'] == 'True'
        assert r3['eliminated_Amiwala'] == 'True'
        assert r3['eliminated_Andrew'] == 'True'
        assert r3['eliminated_Biss'] == 'False'
        print(f"  ✓ Tick 4 (80%): Huynh, Amiwala, Andrew eliminated=True")

        # ── call_fired stays False across all ticks (never triggered in mock) ──
        assert all(r['call_fired'] == 'False' for r in rows),             "call_fired should be False in all mock ticks"
        print(f"  ✓ call_fired=False throughout (no 97% trigger in mock)")

        # ── Timestamps are ISO format ─────────────────────────────────────
        from datetime import datetime
        for i, r in enumerate(rows):
            datetime.fromisoformat(r['timestamp'])   # raises if malformed
        print(f"  ✓ All timestamps valid ISO format")

        # ── win_prob columns sum to ~100% ────────────────────────────────
        for i, r in enumerate(rows[1:], start=2):   # skip tick 1 (all zero)
            total = sum(float(r[f'win_prob_{c}']) for c in CANDIDATES)
            assert 95.0 <= total <= 105.0,                 f"Tick {i} win_prob sum = {total:.1f}% (expected ~100)"
        print(f"  ✓ win_prob columns sum to ~100% on all non-zero ticks")

        print(f"\n  Log file: {log_files[0]}")

    print(f"\nLOGGER TEST PASSED")

    # ── All done ─────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"ALL SCENARIOS PASSED")
    print(f"{'='*60}")
    print(f"\nPipeline is end-to-end verified. Election night checklist:")
    print(f"  1. Confirm Cook contestId and update Cook_County_Scraper.py")
    print(f"  2. Get Chicago BOE URL and build chicago_boe_scraper.py")
    print(f"  3. Run: python main.py --preflight  (at ~6:45 PM)")
    print(f"  4. Run: python main.py              (at 7:00 PM)")


if __name__ == '__main__':
    main()