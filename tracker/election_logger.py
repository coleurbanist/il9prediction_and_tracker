"""
Election Night CSV Logger
=========================
Writes one row per tick to election_night_log_{date}.csv.

Columns:
    timestamp           ISO-8601 datetime
    tick                integer tick counter
    pct_reported        district-wide % reporting (0-100)
    pct_chicago         Chicago % reporting
    pct_cook            Cook County % reporting
    pct_lake            Lake County % reporting
    pct_mchenry         McHenry County % reporting
    votes_{c}           raw vote total per candidate
    share_{c}           actual vote share % per candidate
    win_prob_{c}        Monte Carlo win probability % per candidate
    p90_{c}             90th percentile vote share % per candidate
    projected_winner    candidate name with highest win_prob (or '' if <50%)
    call_fired          True once the >=97% win-prob call has been made
    eliminated_{c}      True once candidate has been eliminated

Usage:
    from election_logger import ElectionLogger
    logger = ElectionLogger()               # creates file, writes header
    logger.log(tick, merged, win_probs, ceiling, eliminated, call_fired)
"""

import csv
import os
from datetime import datetime

CANDIDATES = ['Biss', 'Abughazaleh', 'Fine', 'Simmons', 'Andrew', 'Amiwala', 'Huynh']

# Build column order once
_CANDIDATE_COLS = []
for c in CANDIDATES:
    _CANDIDATE_COLS += [f'votes_{c}', f'share_{c}', f'win_prob_{c}', f'p90_{c}']
for c in CANDIDATES:
    _CANDIDATE_COLS.append(f'eliminated_{c}')

COLUMNS = (
    ['timestamp', 'tick', 'pct_reported',
     'pct_chicago', 'pct_cook', 'pct_lake', 'pct_mchenry']
    + _CANDIDATE_COLS
    + ['projected_winner', 'call_fired']
)


class ElectionLogger:
    def __init__(self, log_dir=None):
        """
        Creates the CSV file in log_dir (defaults to the tracker/ directory).
        File is named election_night_log_YYYY-MM-DD.csv.
        """
        if log_dir is None:
            log_dir = os.path.dirname(os.path.abspath(__file__))

        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f'election_night_log_{date_str}.csv'
        self.path = os.path.join(log_dir, filename)

        self._file = open(self.path, 'w', newline='', encoding='utf-8')
        self._writer = csv.DictWriter(self._file, fieldnames=COLUMNS)
        self._writer.writeheader()
        self._file.flush()

        print(f"[ElectionLogger] Logging to {self.path}")

    def log(self, tick, merged, win_probs, ceiling, eliminated, call_fired):
        """
        Write one row for the current tick.

        Args:
            tick        int — tick counter
            merged      dict — output of merge_district()
            win_probs   dict — {candidate: float (0-100)}
            ceiling     dict — {candidate: float} p90 vote share
            eliminated  set  — candidates eliminated so far (cumulative)
            call_fired  bool — True once >=97% call has been made
        """
        now = datetime.now().isoformat(timespec='seconds')
        j_pct = merged.get('jurisdiction_pct', {})
        actual = merged.get('actual_share', {})
        votes  = merged.get('votes', {})

        row = {
            'timestamp':    now,
            'tick':         tick,
            'pct_reported': round(merged.get('pct_reported', 0) * 100, 2),
            'pct_chicago':  round(j_pct.get('chicago', 0) * 100, 2),
            'pct_cook':     round(j_pct.get('cook', 0) * 100, 2),
            'pct_lake':     round(j_pct.get('lake', 0) * 100, 2),
            'pct_mchenry':  round(j_pct.get('mchenry', 0) * 100, 2),
        }

        for c in CANDIDATES:
            row[f'votes_{c}']    = int(votes.get(c, 0))
            row[f'share_{c}']    = round(actual.get(c, 0.0), 3)
            row[f'win_prob_{c}'] = round(win_probs.get(c, 0.0), 3)
            row[f'p90_{c}']      = round(ceiling.get(c, 0.0), 3)
            row[f'eliminated_{c}'] = c in eliminated

        # projected_winner: candidate with highest win_prob, only show if >=50%
        leader = max(CANDIDATES, key=lambda c: win_probs.get(c, 0))
        row['projected_winner'] = leader if win_probs.get(leader, 0) >= 50.0 else ''
        row['call_fired'] = call_fired

        self._writer.writerow(row)
        self._file.flush()   # ensure data survives if process is killed

    def close(self):
        self._file.close()
        print(f"[ElectionLogger] Log closed: {self.path}")