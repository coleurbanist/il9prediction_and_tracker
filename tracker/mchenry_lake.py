"""
Lake and McHenry County scraper for IL-09 Democratic Primary results.
Source: civicAPI — https://civicapi.org/api/v2/race/55578

Single API call returns both counties. No authentication required.
Attribution required: civicapi.org

Response structure:
    race_data['region_results'] -> dict of region objects
    Each region: {
        'name': 'Lake' | 'McHenry' | 'Cook',
        'type': 'County',
        'percent_reporting': float,
        'candidates': [
            {'name': str, 'votes': int, 'percent': float, 'winner': bool}, ...
        ]
    }

Usage:
    scraper = LakeMcHenryScraper()
    results = scraper.fetch()
    # results['lake']     -> {'candidates': {...}, 'pct_reporting': float}
    # results['mchenry']  -> {'candidates': {...}, 'pct_reporting': float}
    # results['combined'] -> {'candidates': {...}} (Lake + McHenry summed)
"""

import requests
import logging

logger = logging.getLogger(__name__)

CIVICAPI_URL = 'https://civicapi.org/api/v2/race/55578'

# Candidate name mapping: civicAPI full name -> internal short name
# Adjust if civicAPI name doesn't exactly match — verified from API response
CANDIDATE_NAME_MAP = {
    'Daniel K. Biss':   'Biss',
    'Kat Abughazaleh':  'Abughazaleh',
    'Laura Fine':       'Fine',
    'Mike Simmons':     'Simmons',
    'Phil Andrew':      'Andrew',
    'Bushra Amiwala':   'Amiwala',
    'Hoan Huynh':       'Huynh',
    # Unpolled candidates — included so totals are complete
    'Bethany Johnson':  'Johnson',
    'Howard Rosenblum': 'Rosenblum',
    'Jeff Cohen':       'Cohen',
    'Justin Ford':      'Ford',
    'Mark Fredrickson': 'Fredrickson',
    'Nick Pyati':       'Pyati',
    'Patricia Brown':   'Brown',
    'Sam Polan':        'Polan',
    'Write-in':         'Write-in',
}

TRACKED_COUNTIES = ('Lake', 'McHenry')


class LakeMcHenryScraper:
    def __init__(self, url=CIVICAPI_URL):
        self.url = url
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; IL09ElectionTracker/1.0)',
            'Accept': 'application/json',
        })

    def fetch(self):
        """
        Fetch civicAPI results and return Lake and McHenry data.

        Returns dict:
            lake     : {'candidates': {short_name: votes}, 'pct_reporting': float,
                        'candidates_raw': {full_name: votes}}
            mchenry  : same structure
            combined : {'candidates': {short_name: votes}} (Lake + McHenry summed)
            raw      : full API response dict
        Returns None on fetch failure.
        """
        try:
            resp = self.session.get(self.url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except requests.RequestException as e:
            logger.error(f'civicAPI fetch failed: {e}')
            return None
        except ValueError as e:
            logger.error(f'civicAPI JSON parse failed: {e}')
            return None

        return self._parse(data)

    def _parse(self, data):
        region_results = data.get('region_results', {})

        county_data = {}
        for region in region_results.values():
            name = region.get('name', '')
            if name not in TRACKED_COUNTIES:
                continue

            pct_reporting = region.get('percent_reporting', 0.0)
            candidates_raw = {}
            candidates = {}

            for c in region.get('candidates', []):
                full_name = c.get('name', '')
                votes = c.get('votes', 0)
                candidates_raw[full_name] = votes
                short_name = CANDIDATE_NAME_MAP.get(full_name, full_name)
                candidates[short_name] = votes

            county_data[name.lower()] = {
                'candidates': candidates,
                'candidates_raw': candidates_raw,
                'pct_reporting': pct_reporting / 100.0 if pct_reporting > 1 else pct_reporting,
                'winner': _get_winner(region.get('candidates', [])),
            }

        # Build combined Lake + McHenry totals
        combined = {}
        for county in ('lake', 'mchenry'):
            if county in county_data:
                for cand, votes in county_data[county]['candidates'].items():
                    combined[cand] = combined.get(cand, 0) + votes

        # Overall pct_reporting for combined (weighted by expected turnout)
        # Lake ~48% of Lake+McHenry combined, McHenry ~52%
        lake_pct = county_data.get('lake', {}).get('pct_reporting', 0.0)
        mchenry_pct = county_data.get('mchenry', {}).get('pct_reporting', 0.0)
        combined_pct = lake_pct * 0.48 + mchenry_pct * 0.52

        return {
            'lake':     county_data.get('lake',    _empty_county()),
            'mchenry':  county_data.get('mchenry', _empty_county()),
            'combined': {
                'candidates': combined,
                'pct_reporting': combined_pct,
            },
            'raw': data,
        }


def _empty_county():
    return {'candidates': {}, 'candidates_raw': {}, 'pct_reporting': 0.0, 'winner': None}


def _get_winner(candidates):
    """Return short name of winner if any candidate has winner=True, else None."""
    for c in candidates:
        if c.get('winner'):
            return CANDIDATE_NAME_MAP.get(c['name'], c['name'])
    return None


# ---------------------------------------------------------------------------
# Quick test
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    print('Fetching civicAPI race 55578 (IL-09 Democratic Primary)...')
    print('-' * 60)

    scraper = LakeMcHenryScraper()
    results = scraper.fetch()

    if not results:
        print('Fetch failed.')
    else:
        for county in ('lake', 'mchenry'):
            data = results[county]
            print(f"\n{county.upper()} COUNTY")
            print(f"  Pct reporting: {data['pct_reporting']:.1%}")
            print(f"  Winner called: {data['winner']}")
            print(f"  Candidates ({len(data['candidates'])}):")
            for name, votes in sorted(data['candidates'].items(), key=lambda x: -x[1]):
                pct = votes / max(sum(data['candidates'].values()), 1) * 100
                print(f"    {name:<20} {votes:>6}  ({pct:.1f}%)")

        print(f"\nCOMBINED (Lake + McHenry)")
        print(f"  Pct reporting: {results['combined']['pct_reporting']:.1%}")
        combined = results['combined']['candidates']
        total = max(sum(combined.values()), 1)
        for name, votes in sorted(combined.items(), key=lambda x: -x[1]):
            pct = votes / total * 100
            print(f"  {name:<20} {votes:>6}  ({pct:.1f}%)")

        # Verify all 7 modeled candidates present
        print(f"\nMODELED CANDIDATE CHECK:")
        modeled = ['Biss', 'Abughazaleh', 'Fine', 'Simmons', 'Andrew', 'Amiwala', 'Huynh']
        lake_cands = results['lake']['candidates']
        for c in modeled:
            status = '✅' if c in lake_cands else '❌ MISSING'
            print(f"  {c}: {status}")