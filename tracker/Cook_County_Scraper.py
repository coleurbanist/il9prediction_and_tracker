"""
Cook County scraper for IL-09 Democratic Primary results.
Source: results326.cookcountyclerkil.gov

Structure:
- One <table> per township, each ending with a "[Township] Township Results" summary row
- Candidate columns are positional — read from <thead> on each table
- Precincts show 0 until reported; zero-tracking distinguishes unreported from reported-zero
- Townships in IL-09: Evanston, Maine, New Trier, Niles, Northfield, Wheeling

Usage:
    scraper = CookCountyScraper(contest_id=YOUR_CONTEST_ID)
    results = scraper.fetch()
    # results['precincts']  -> dict of precinct_name -> {candidate: votes}
    # results['reported']   -> set of precinct names that have ever shown non-zero
    # results['totals']     -> dict of candidate -> total votes across Cook
    # results['pct_reporting'] -> float 0-1
"""

import requests
from bs4 import BeautifulSoup
import logging
import time

logger = logging.getLogger(__name__)

# Candidates to track — must match names as they appear in the <thead> of the results page.
# Populated dynamically from the page header; this list is used for fuzzy matching.
CANDIDATE_LAST_NAMES = [
    'Biss', 'Abughazaleh', 'Fine', 'Simmons', 'Andrew', 'Amiwala', 'Huynh',
    # unpolled candidates — include so we capture their votes for totals
    'Johnson', 'Rosenblum', 'Cohen', 'Ford', 'Fredrickson', 'Pyati', 'Brown', 'Polan',
]

TOWNSHIPS = ['Evanston', 'Maine', 'New Trier', 'Niles', 'Northfield', 'Wheeling']

BASE_URL = 'https://results326.cookcountyclerkil.gov'

# contest_id for the IL-09 Democratic primary — update once page goes live
# For reference: 2024 general was contestId=13 at results1124.cookcountyclerkil.gov
CONTEST_ID = None  #


class CookCountyScraper:
    def __init__(self, contest_id=None, url=None):
        """
        Provide either contest_id (preferred) or a full URL override for testing.
        """
        if url:
            self.url = url
        elif contest_id:
            self.url = f'{BASE_URL}/Home/Detail?contestId={contest_id}'
        else:
            raise ValueError('Provide contest_id or url')

        # Zero-tracking: set of precinct names that have ever shown non-zero votes.
        # A precinct absent from this set is unreported, even if it shows 0.
        self._ever_nonzero = set()

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; IL09ElectionTracker/1.0)',
        })

    def fetch(self):
        """
        Fetch and parse Cook County results page.

        Returns dict:
            candidates      : list of candidate name strings (from page header)
            precincts       : dict[precinct_name] -> dict[candidate] -> votes (int)
            reported        : set of precinct names with ever-nonzero votes
            unreported      : set of precinct names with all-zero votes
            township_totals : dict[township] -> dict[candidate] -> votes
            totals          : dict[candidate] -> int (sum across all Cook precincts)
            total_precincts : int
            precincts_reporting : int
            pct_reporting   : float (0.0 - 1.0)
            precinct_voter_totals : dict[precinct_name] -> int (total votes cast)
        """
        try:
            resp = self.session.get(self.url, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error(f'Cook County fetch failed: {e}')
            return None

        return self._parse(resp.text)

    def _parse(self, html):
        soup = BeautifulSoup(html, 'html.parser')

        # --- Parse overall precinct reporting count from header ---
        # "222 of 222 Precincts Reported"
        total_precincts = 0
        precincts_reporting = 0
        header_info = soup.find('td', class_='progressbar-wrapper percent border-0 font-weight-bold')
        if header_info:
            text = header_info.get_text(strip=True)
            # e.g. "0 of 222 Precincts Reported"
            parts = text.split()
            try:
                precincts_reporting = int(parts[0])
                total_precincts = int(parts[2])
            except (IndexError, ValueError):
                logger.warning(f'Could not parse precinct count from: {text}')

        # --- Find all precinct tables ---
        # Each township has its own <table class="table verticaltext ...">
        all_precincts = {}
        township_totals = {}
        all_candidates = None

        tables = soup.find_all('table', class_=lambda c: c and 'verticaltext' in c)

        for table in tables:
            # Read candidate names from <thead>
            thead = table.find('thead')
            if not thead:
                continue

            header_cells = thead.find_all('th')
            # Columns: Precinct | Registered Voters | Ballots Cast | [candidates...] | Total Votes
            # Candidate columns start at index 3, end before last column
            candidate_names = []
            for th in header_cells[3:-1]:
                name = th.get_text(strip=True)
                if name:
                    candidate_names.append(name)

            if all_candidates is None and candidate_names:
                all_candidates = candidate_names

            if not candidate_names:
                continue

            # Read precinct rows from <tbody>
            tbody = table.find('tbody')
            if not tbody:
                continue

            current_township = None

            for row in tbody.find_all('tr'):
                cells = row.find_all('td')
                if len(cells) < 4:
                    continue

                precinct_raw = cells[0].get_text(strip=True)

                # Detect township summary row
                if 'Township Results' in precinct_raw:
                    township_name = precinct_raw.replace('Township Results', '').strip()
                    current_township = township_name
                    # Parse township totals
                    twp_votes = {}
                    for i, cand in enumerate(candidate_names):
                        try:
                            v = int(cells[3 + i].get_text(strip=True).replace(',', ''))
                        except (ValueError, IndexError):
                            v = 0
                        twp_votes[cand] = v
                    township_totals[township_name] = twp_votes
                    continue

                # Regular precinct row
                # Determine township from precinct name prefix
                township = _township_from_precinct(precinct_raw)

                # Parse candidate votes (positional)
                candidate_votes = {}
                total_votes = 0
                for i, cand in enumerate(candidate_names):
                    try:
                        v = int(cells[3 + i].get_text(strip=True).replace(',', ''))
                    except (ValueError, IndexError):
                        v = 0
                    candidate_votes[cand] = v
                    total_votes += v

                # Parse total votes cast (last bold cell)
                try:
                    voter_total = int(cells[-1].get_text(strip=True).replace(',', ''))
                except (ValueError, IndexError):
                    voter_total = total_votes

                # Normalize precinct name for model lookup
                precinct_key = _normalize_precinct_name(precinct_raw)

                all_precincts[precinct_key] = {
                    'township': township,
                    'candidates': candidate_votes,
                    'voter_total': voter_total,
                    'raw_name': precinct_raw,
                }

                # Zero-tracking: mark as reported if any candidate has non-zero votes
                if any(v > 0 for v in candidate_votes.values()):
                    self._ever_nonzero.add(precinct_key)

        # Build totals by summing all precincts
        # (unreported precincts show 0 so summing everything is correct)
        totals = {}
        if all_candidates:
            for cand in all_candidates:
                totals[cand] = sum(
                    p['candidates'].get(cand, 0) for p in all_precincts.values()
                )

        reported = self._ever_nonzero.copy()
        unreported = set(all_precincts.keys()) - reported

        pct_reporting = (
            len(reported) / len(all_precincts) if all_precincts else 0.0
        )

        return {
            'candidates': all_candidates or [],
            'precincts': {k: v['candidates'] for k, v in all_precincts.items()},
            'precinct_meta': {k: {'township': v['township'], 'voter_total': v['voter_total']} for k, v in all_precincts.items()},
            'reported': reported,
            'unreported': unreported,
            'township_totals': township_totals,
            'totals': totals,
            'total_precincts': total_precincts or len(all_precincts),
            'precincts_reporting': len(reported),
            'pct_reporting': pct_reporting,
        }


def _township_from_precinct(raw_name):
    """Infer township from precinct name prefix."""
    raw_lower = raw_name.lower()
    for t in TOWNSHIPS:
        if raw_lower.startswith(t.lower()):
            return t
    return 'Unknown'


def _normalize_precinct_name(raw_name):
    """
    Normalize Cook County precinct names to match IL_09_precinct_probabilities.csv.

    CSV formats:
        Evanston  -> 'Evanston Ward 1 Precinct 1'   (Ward + Precinct, already correct)
        Others    -> 'Maine Precinct 8'              (Township + Precinct + number)

    Raw HTML formats:
        Evanston  -> 'Evanston Ward 1 Precinct 1 '  (trailing space only, already correct)
        Others    -> 'Maine   8 '                   (multiple spaces, no 'Precinct' word)
    """
    import re
    name = re.sub(r'\s+', ' ', raw_name).strip()

    # Non-Evanston precincts: "Maine 8" -> "Maine Precinct 8"
    # Detect: starts with a township name, followed by a space and a number (no 'Ward'/'Precinct')
    for township in TOWNSHIPS:
        if name.startswith(township) and 'Ward' not in name and 'Precinct' not in name:
            suffix = name[len(township):].strip()
            return f'{township} Precinct {suffix}'

    return name


# ---------------------------------------------------------------------------
# Quick test — fetch live 2024 general page and print summary
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    TEST_URL = 'https://results1124.cookcountyclerkil.gov/Home/Detail?contestId=13'
    print(f'Fetching test page: {TEST_URL}')
    print('(This is the 2024 general — structure should match 2026 primary)')
    print('-' * 60)

    scraper = CookCountyScraper(url=TEST_URL)
    results = scraper.fetch()

    if not results:
        print('Fetch failed.')
    else:
        print(f"Candidates found ({len(results['candidates'])}):")
        for c in results['candidates']:
            print(f"  {c}")

        print(f"\nPrecincts total:     {results['total_precincts']}")
        print(f"Precincts reporting: {results['precincts_reporting']}")
        print(f"Pct reporting:       {results['pct_reporting']:.1%}")

        print(f"\nTownship totals:")
        for twp, votes in results['township_totals'].items():
            total = sum(votes.values())
            print(f"  {twp}: {total:,} votes")

        print(f"\nDistrict-wide totals:")
        for cand, votes in sorted(results['totals'].items(), key=lambda x: -x[1]):
            pct = votes / sum(results['totals'].values()) * 100 if sum(results['totals'].values()) > 0 else 0
            print(f"  {cand}: {votes:,} ({pct:.1f}%)")

        print(f"\nSample precincts (first 5):")
        for i, (name, votes) in enumerate(results['precincts'].items()):
            if i >= 5:
                break
            print(f"  '{name}' -> {votes}")

        print(f"\nReported: {len(results['reported'])} precincts")
        print(f"Unreported: {len(results['unreported'])} precincts")

        # --- Optional: validate against IL_09_precinct_probabilities.csv ---
        import os, csv as csv_mod
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'data', 'csv_data', 'expectations', 'IL_09_precinct_probabilities.csv'
        )
        if os.path.exists(csv_path):
            print(f'\n{"=" * 60}')
            print('PRECINCT NAME VALIDATION vs CSV')
            print('=' * 60)
            csv_cook = set()
            with open(csv_path) as f:
                for row in csv_mod.DictReader(f):
                    if row.get('in_cook') == '1' and row.get('in_chicago') != '1':
                        csv_cook.add(row['precinct_name'])

            scraper_names = set(results['precincts'].keys())
            matched = scraper_names & csv_cook
            only_scraper = scraper_names - csv_cook
            only_csv = csv_cook - scraper_names

            print(f'CSV Cook precincts:     {len(csv_cook)}')
            print(f'Scraper precincts:      {len(scraper_names)}')
            print(f'Matched:                {len(matched)}')

            if only_scraper:
                print(f'\nIn scraper but NOT in CSV ({len(only_scraper)}):')
                for n in sorted(only_scraper):
                    print(f'  {repr(n)}')
            else:
                print('\n✅ All scraper precincts found in CSV')

            if only_csv:
                print(f'\nIn CSV but NOT in scraper ({len(only_csv)}):')
                for n in sorted(only_csv):
                    print(f'  {repr(n)}')
            else:
                print('✅ All CSV precincts found in scraper')
        else:
            print(f'\n(CSV not found at {csv_path} — skipping validation)')