"""
Cook County Precinct-Level Expectation Engine
==============================================
Loads per-precinct model expectations from IL_09_precinct_probabilities.csv
and provides two functions used by tracker_main.py:

    cook_adjusted_expected(reported_precincts)
        → {candidate: float}  per-candidate expected % given which precincts
                               have reported (for +/- delta display in bot posts)

    cook_blended_votes(precinct_results, total_cook_model_votes)
        → {candidate: float}  blended vote estimate combining actual reported
                               precinct results with model projections for
                               unreported precincts (for simulation baseline)

Both functions use the `final_` columns from the CSV, which are the
fully-adjusted per-precinct expectations incorporating geo boosts,
senate district crosstabs, and poll scaling.

Usage in tracker_main.py:
    from cook_precinct_expectations import CookPrecinctExpectations
    cook_exp = CookPrecinctExpectations()   # load once at startup

    # In the merge step, pass Cook scraper's precincts dict:
    adjusted_exp = cook_exp.adjusted_expected(reported_precinct_names)
    blended      = cook_exp.blended_shares(cook_scraper_result)
"""

import csv
import os

CANDIDATES = ['Biss', 'Abughazaleh', 'Fine', 'Simmons', 'Andrew', 'Amiwala', 'Huynh']

# Path relative to tracker/ directory
CSV_PATH = os.path.join(
    os.path.dirname(__file__),
    '..', 'data', 'csv_data', 'expectations', 'IL_09_precinct_probabilities.csv'
)


class CookPrecinctExpectations:
    """
    Loads Cook County precinct-level model expectations at startup.
    Provides adjusted expected shares and blended vote estimates
    based on which precincts have actually reported.
    """

    def __init__(self, csv_path=CSV_PATH):
        self.precincts = {}      # {precinct_name: {candidate: pct, 'turnout': int}}
        self.total_model_votes = 0
        self._load(csv_path)

    def _load(self, path):
        with open(path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Only Cook non-Chicago precincts
                if row.get('in_cook') != '1' or row.get('in_chicago') == '1':
                    continue
                name = row['precinct_name'].strip()
                if not name:
                    continue
                turnout = float(row.get('estimated_turnout') or 0)
                self.precincts[name] = {
                    c: float(row.get(f'final_{c}') or 0)
                    for c in CANDIDATES
                }
                self.precincts[name]['turnout'] = turnout
                self.total_model_votes += turnout

        print(f"[CookPrecinctExpectations] Loaded {len(self.precincts)} Cook precincts "
              f"({self.total_model_votes:,.0f} projected votes)")

    # ── Public API ────────────────────────────────────────────────────────

    def adjusted_expected(self, reported_precinct_names):
        """
        Given a set/list of precinct names that have reported,
        returns the turnout-weighted expected share for each candidate
        across only those precincts.

        This is the denominator for the +/- delta shown in bot posts:
        "Biss is at 32% vs 30.4% expected from these precincts" → +1.6

        If no reported precincts match the model, falls back to
        the Cook-wide model average.

        Returns: {candidate: float (0-100)}
        """
        matched = [
            (name, self.precincts[name])
            for name in reported_precinct_names
            if name in self.precincts
        ]

        if not matched:
            return self._cook_wide_average()

        total_weight = sum(p['turnout'] for _, p in matched)
        if total_weight == 0:
            return self._cook_wide_average()

        return {
            c: sum(p[c] * p['turnout'] for _, p in matched) / total_weight
            for c in CANDIDATES
        }

    def blended_shares(self, cook_scraper_result):
        """
        Combines actual reported precinct votes with model projections
        for unreported precincts to produce a blended Cook-wide share.

        cook_scraper_result: the dict returned by CookCountyScraper.fetch()
            Must have:
                'precincts': {precinct_name: {candidate: votes}}
                'reported':  set of reported precinct names
                'totals':    {candidate: int}  (actual votes across all reported)

        Returns: {candidate: float (0-100)} blended share estimate

        Logic:
            - Reported precincts: use actual votes
            - Unreported precincts: use model expected votes
              (final_pct * estimated_turnout)
            - Sum both, normalize to percentages
        """
        reported = cook_scraper_result.get('reported', set())
        precinct_votes = cook_scraper_result.get('precincts', {})

        blended_votes = {c: 0.0 for c in CANDIDATES}

        # Actual votes from reported precincts
        for precinct_name in reported:
            p_votes = precinct_votes.get(precinct_name, {})
            for c in CANDIDATES:
                blended_votes[c] += p_votes.get(c, 0)

        # Model projections for unreported precincts
        unreported_names = set(self.precincts.keys()) - set(reported)
        for name in unreported_names:
            model = self.precincts[name]
            turnout = model['turnout']
            for c in CANDIDATES:
                blended_votes[c] += (model[c] / 100.0) * turnout

        total = sum(blended_votes.values())
        if total == 0:
            return self._cook_wide_average()

        return {c: blended_votes[c] / total * 100 for c in CANDIDATES}

    def match_rate(self, reported_precinct_names):
        """
        Returns fraction of reported precinct names found in the model.
        Use this to warn if precinct name formats don't match.
        """
        if not reported_precinct_names:
            return 1.0
        matched = sum(1 for n in reported_precinct_names if n in self.precincts)
        return matched / len(reported_precinct_names)

    # ── Internal ──────────────────────────────────────────────────────────

    def _cook_wide_average(self):
        """Turnout-weighted average across all 222 Cook precincts."""
        if self.total_model_votes == 0:
            return {c: 100.0 / len(CANDIDATES) for c in CANDIDATES}
        return {
            c: sum(
                p[c] * p['turnout'] for p in self.precincts.values()
            ) / self.total_model_votes
            for c in CANDIDATES
        }