"""
Bluesky bot for IL-09 Democratic Primary election night.

Posts a fresh thread every 5 minutes with current results.
Fires an immediate thread on:
  - Mathematical elimination of a candidate
  - Win probability >= 97% (projected winner)

Thread structure:
  1. Root post — district-wide standings (Phase 1 or Phase 2 format)
  2. Regional sub-posts — one per jurisdiction once >= 25% reporting
  3. Special post — elimination or projected winner (if triggered)
  4. Attribution reply — "Lake and McHenry results via civicAPI / civicapi.org"

Setup:
  pip install atproto python-dotenv

.env file (never commit this):
  BSKY_HANDLE=yourhandle.bsky.social
  BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx

Usage:
  bot = BlueskyBot()
  bot.post_thread(combined_results)        # normal 5-min update
  bot.post_elimination(candidate_name)     # immediate trigger
  bot.post_projected_winner(candidate)     # immediate trigger
"""

import os
import time
import logging
from datetime import datetime

from dotenv import load_dotenv
from atproto import Client

load_dotenv()
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Model expected vote shares by jurisdiction (for +/- calculation)
# District, Chicago, Cook, Lake, McHenry
EXPECTED_SHARES = {
    'Biss':        {'district': 0.295, 'chicago': 0.268, 'cook': 0.312, 'lake': 0.282, 'mchenry': 0.295},
    'Abughazaleh': {'district': 0.234, 'chicago': 0.263, 'cook': 0.206, 'lake': 0.236, 'mchenry': 0.234},
    'Fine':        {'district': 0.178, 'chicago': 0.149, 'cook': 0.194, 'lake': 0.221, 'mchenry': 0.211},
    'Simmons':     {'district': 0.104, 'chicago': 0.140, 'cook': 0.084, 'lake': 0.061, 'mchenry': 0.063},
    'Andrew':      {'district': 0.077, 'chicago': 0.050, 'cook': 0.096, 'lake': 0.088, 'mchenry': 0.083},
    'Amiwala':     {'district': 0.068, 'chicago': 0.076, 'cook': 0.060, 'lake': 0.060, 'mchenry': 0.059},
    'Huynh':       {'district': 0.022, 'chicago': 0.026, 'cook': 0.016, 'lake': 0.022, 'mchenry': 0.023},
}

# Display thresholds (fraction 0-1)
DISPLAY_THRESHOLD_DISTRICT = 0.50
DISPLAY_THRESHOLD_CHICAGO = 0.25
DISPLAY_THRESHOLD_COOK = 0.25
DISPLAY_THRESHOLD_JURISDICTION = 0.25  # for regional sub-posts

# Win probability threshold for projected winner call
WIN_PROB_THRESHOLD = 0.97

# Bluesky character limit
BSKY_CHAR_LIMIT = 300

# Candidates to show in posts (top 5 by votes, from this ordered list)
MODELED_CANDIDATES = ['Biss', 'Abughazaleh', 'Fine', 'Simmons', 'Andrew', 'Amiwala', 'Huynh']


# ---------------------------------------------------------------------------
# Bot
# ---------------------------------------------------------------------------

class BlueskyBot:
    def __init__(self, dry_run=False):
        """
        dry_run=True: print posts to console instead of sending to Bluesky.
        """
        self.dry_run = dry_run
        self.client = None
        self._last_post_time = 0
        self._eliminated = set()  # candidates already announced as eliminated

        if not dry_run:
            self._login()

    def _login(self):
        handle = os.getenv('BSKY_HANDLE')
        password = os.getenv('BSKY_APP_PASSWORD')
        if not handle or not password:
            raise ValueError(
                'BSKY_HANDLE and BSKY_APP_PASSWORD must be set in .env file.\n'
                'Generate an app password at: https://bsky.app/settings/app-passwords'
            )
        self.client = Client()
        self.client.login(handle, password)
        logger.info(f'Logged in to Bluesky as {handle}')

    # -----------------------------------------------------------------------
    # Public interface
    # -----------------------------------------------------------------------

    def should_post_update(self):
        """Returns True if 5 minutes have elapsed since last post."""
        return (time.time() - self._last_post_time) >= 300

    def post_thread(self, results, win_prob=None, projected_winner=None):
        """
        Post a full results thread. Call this on the 5-minute timer
        or immediately on a trigger event.

        results: dict with keys:
            district    : {'candidates': {name: votes}, 'pct_reporting': float}
            chicago     : {'candidates': {name: votes}, 'pct_reporting': float}
            cook        : {'candidates': {name: votes}, 'pct_reporting': float}
            lake        : {'candidates': {name: votes}, 'pct_reporting': float}
            mchenry     : {'candidates': {name: votes}, 'pct_reporting': float}
        win_prob: dict of {candidate: float} or None
        projected_winner: str candidate name or None
        """
        thresholds_met = self._thresholds_met(results)

        # Build post texts
        root_text = self._format_root(results, win_prob, projected_winner, thresholds_met)
        regional_posts = self._format_regional(results, thresholds_met)
        attribution_text = 'Lake and McHenry County results via civicAPI\ncivicapi.org'

        # Post the thread
        root_ref = self._post(root_text)
        if root_ref is None:
            return

        parent_ref = root_ref
        for text in regional_posts:
            reply_ref = self._reply(text, root_ref, parent_ref)
            if reply_ref:
                parent_ref = reply_ref

        # Attribution always last
        self._reply(attribution_text, root_ref, parent_ref)

        self._last_post_time = time.time()

    def post_eliminations(self, candidates, results):
        """
        Post a single elimination thread for one or more candidates.
        Skips candidates already announced. No-ops if all already announced.

        candidates: set or list of candidate short names
        """
        new_ones = [c for c in candidates if c not in self._eliminated]
        if not new_ones:
            return
        for c in new_ones:
            self._eliminated.add(c)

        if len(new_ones) == 1:
            names_str = new_ones[0]
            verb = 'is'
        elif len(new_ones) == 2:
            names_str = f'{new_ones[0]} and {new_ones[1]}'
            verb = 'are'
        else:
            names_str = ', '.join(new_ones[:-1]) + f', and {new_ones[-1]}'
            verb = 'are'

        elim_text = (
            f'{names_str} {verb} projected to not win the IL-09 primary.'
        )
        root_ref = self._post(elim_text)

        if root_ref:
            thresholds_met = self._thresholds_met(results)
            standings = self._format_root(results, None, None, thresholds_met)
            self._reply(standings, root_ref, root_ref)
            self._reply('Lake and McHenry County results via civicAPI\ncivicapi.org', root_ref, root_ref)

        self._last_post_time = time.time()

    def post_elimination(self, candidate_name, results):
        """Single-candidate convenience wrapper — delegates to post_eliminations."""
        self.post_eliminations([candidate_name], results)

    def post_projected_winner(self, candidate_name, win_prob_pct, results):
        """Post an immediate projected winner thread."""
        winner_text = (
            f'📊 {candidate_name} is projected to win the IL-09 Democratic primary '
            f'({win_prob_pct:.0f}% probability).'
        )
        root_ref = self._post(winner_text)

        if root_ref:
            thresholds_met = self._thresholds_met(results)
            wp_dict = {candidate_name: win_prob_pct / 100.0}
            standings = self._format_root(results, wp_dict, candidate_name, thresholds_met)
            self._reply(standings, root_ref, root_ref)
            self._reply('Lake and McHenry County results via civicAPI\ncivicapi.org', root_ref, root_ref)

        self._last_post_time = time.time()

    # -----------------------------------------------------------------------
    # Formatting
    # -----------------------------------------------------------------------

    def _thresholds_met(self, results):
        """Check if all three display thresholds are met for Phase 2."""
        return (
            results.get('district', {}).get('pct_reporting', 0) >= DISPLAY_THRESHOLD_DISTRICT
            and results.get('chicago', {}).get('pct_reporting', 0) >= DISPLAY_THRESHOLD_CHICAGO
            and results.get('cook', {}).get('pct_reporting', 0) >= DISPLAY_THRESHOLD_COOK
        )

    def _format_root(self, results, win_prob, projected_winner, thresholds_met):
        """
        Format the root post.

        Phase 1 (before thresholds): shares only, no +/-
        Phase 2 (after thresholds): shares + +/- + win probability
        """
        district = results.get('district', {})
        chicago = results.get('chicago', {})
        cook = results.get('cook', {})
        lake = results.get('lake', {})
        mchenry = results.get('mchenry', {})

        dist_pct = district.get('pct_reporting', 0)
        chi_pct = chicago.get('pct_reporting', 0)
        cook_pct = cook.get('pct_reporting', 0)
        lake_pct = lake.get('pct_reporting', 0)
        mch_pct = mchenry.get('pct_reporting', 0)

        header = (
            f"{dist_pct:.0%} in est. | "
            f"Chi {chi_pct:.0%} | "
            f"Cook {cook_pct:.0%} | "
            f"Lake {lake_pct:.0%} | "
            f"McH {mch_pct:.0%}"
        )

        # Top 5 candidates by district votes
        dist_candidates = district.get('candidates', {})
        top5 = _top5(dist_candidates, MODELED_CANDIDATES)

        lines = [header, '']
        for cand in top5:
            votes = dist_candidates.get(cand, 0)
            total = max(sum(dist_candidates.values()), 1)
            share = votes / total * 100

            if thresholds_met:
                exp = EXPECTED_SHARES.get(cand, {}).get('district', 0) * 100
                delta = share - exp
                sign = '+' if delta >= 0 else ''
                lines.append(f"{cand} {share:.1f}% ({sign}{delta:.1f})")
            else:
                lines.append(f"{cand} {share:.1f}%")

        # Remove trailing blank line
        if lines and lines[-1] == '':
            lines.pop()

        # Projected winner line
        if projected_winner and thresholds_met:
            wp = win_prob.get(projected_winner, 0) * 100 if win_prob else 0
            lines.append('')
            lines.append(f"📊 {projected_winner} projected to win  ({wp:.0f}% probability)")

        text = '\n'.join(lines)
        return _truncate(text)

    def _format_regional(self, results, thresholds_met):
        """
        Format regional sub-posts for each jurisdiction over 25% reporting.
        Returns list of post strings (may be empty if no jurisdictions qualify).
        """
        posts = []
        jurisdictions = [
            ('Chicago', 'chicago'),
            ('Cook County', 'cook'),
            ('Lake County', 'lake'),
            ('McHenry County', 'mchenry'),
        ]

        for label, key in jurisdictions:
            jur = results.get(key, {})
            pct = jur.get('pct_reporting', 0)
            if pct < DISPLAY_THRESHOLD_JURISDICTION:
                continue

            candidates = jur.get('candidates', {})
            top5 = _top5(candidates, MODELED_CANDIDATES)
            total = max(sum(candidates.values()), 1)

            lines = [f"{label} — {pct:.0%} reporting"]
            for cand in top5:
                votes = candidates.get(cand, 0)
                share = votes / total * 100
                exp = EXPECTED_SHARES.get(cand, {}).get(key, 0) * 100
                delta = share - exp
                sign = '+' if delta >= 0 else ''
                lines.append(f"{cand} {share:.1f}% ({sign}{delta:.1f})")

            posts.append(_truncate('\n'.join(lines)))

        return posts

    # -----------------------------------------------------------------------
    # Bluesky posting
    # -----------------------------------------------------------------------

    def _post(self, text):
        """Post a new root post. Returns post reference or None."""
        self._print_post('ROOT', text)
        if self.dry_run:
            return _mock_ref()
        try:
            response = self.client.send_post(text=text)
            return {'uri': response.uri, 'cid': response.cid}
        except Exception as e:
            logger.error(f'Failed to post: {e}')
            return None

    def _reply(self, text, root_ref, parent_ref):
        """Post a reply in a thread. Returns post reference or None."""
        self._print_post('REPLY', text)
        if self.dry_run:
            return _mock_ref()
        try:
            from atproto_client.models.app.bsky.feed.post import ReplyRef
            from atproto_client.models.com.atproto.repo.strong_ref import Main as StrongRef
            reply = ReplyRef(
                root=StrongRef(uri=root_ref['uri'], cid=root_ref['cid']),
                parent=StrongRef(uri=parent_ref['uri'], cid=parent_ref['cid']),
            )
            response = self.client.send_post(text=text, reply_to=reply)
            return {'uri': response.uri, 'cid': response.cid}
        except Exception as e:
            logger.error(f'Failed to reply: {e}')
            return None

    def _print_post(self, kind, text):
        """Print post to console for dry-run or logging."""
        chars = len(text)
        border = '=' * 60
        logger.info(f'\n{border}\n[{kind}] ({chars} chars)\n{border}\n{text}\n{border}')
        if chars > BSKY_CHAR_LIMIT:
            logger.warning(f'⚠️  POST EXCEEDS {BSKY_CHAR_LIMIT} CHARS ({chars})')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _top5(candidates, ordered_list):
    """Return top 5 candidates by vote total, preserving modeled order for ties."""
    present = {c: candidates.get(c, 0) for c in ordered_list if c in candidates or candidates.get(c, 0) >= 0}
    # Include unmodeled candidates too if they have votes
    for c, v in candidates.items():
        if c not in present:
            present[c] = v
    sorted_cands = sorted(present.keys(), key=lambda c: -present.get(c, 0))
    return sorted_cands[:5]


def _truncate(text):
    """Hard truncate to Bluesky character limit with ellipsis."""
    if len(text) <= BSKY_CHAR_LIMIT:
        return text
    return text[:BSKY_CHAR_LIMIT - 1] + '…'


def _mock_ref():
    """Return a fake post reference for dry-run mode."""
    return {'uri': f'at://mock/{time.time()}', 'cid': 'mock-cid'}


# ---------------------------------------------------------------------------
# Dry-run test
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print('Running dry-run test of BlueskyBot...\n')

    bot = BlueskyBot(dry_run=True)

    # Simulate Phase 1 results (before thresholds)
    mock_results_phase1 = {
        'district': {'pct_reporting': 0.15, 'candidates': {
            'Biss': 1200, 'Abughazaleh': 950, 'Fine': 700,
            'Simmons': 450, 'Andrew': 300, 'Amiwala': 280, 'Huynh': 90,
        }},
        'chicago':  {'pct_reporting': 0.12, 'candidates': {
            'Biss': 500, 'Abughazaleh': 480, 'Fine': 200,
            'Simmons': 300, 'Andrew': 80, 'Amiwala': 150, 'Huynh': 40,
        }},
        'cook':     {'pct_reporting': 0.10, 'candidates': {
            'Biss': 500, 'Abughazaleh': 300, 'Fine': 350,
            'Simmons': 100, 'Andrew': 150, 'Amiwala': 90, 'Huynh': 30,
        }},
        'lake':     {'pct_reporting': 0.05, 'candidates': {
            'Biss': 120, 'Abughazaleh': 90, 'Fine': 80,
            'Simmons': 25, 'Andrew': 40, 'Amiwala': 20, 'Huynh': 10,
        }},
        'mchenry':  {'pct_reporting': 0.05, 'candidates': {
            'Biss': 80, 'Abughazaleh': 80, 'Fine': 70,
            'Simmons': 25, 'Andrew': 30, 'Amiwala': 20, 'Huynh': 10,
        }},
    }

    print('--- PHASE 1 THREAD (before thresholds) ---')
    bot.post_thread(mock_results_phase1)

    # Simulate Phase 2 results (after thresholds)
    mock_results_phase2 = {
        'district': {'pct_reporting': 0.65, 'candidates': {
            'Biss': 8500, 'Abughazaleh': 6800, 'Fine': 5100,
            'Simmons': 3000, 'Andrew': 2200, 'Amiwala': 2000, 'Huynh': 650,
        }},
        'chicago':  {'pct_reporting': 0.60, 'candidates': {
            'Biss': 3200, 'Abughazaleh': 3100, 'Fine': 1500,
            'Simmons': 1800, 'Andrew': 600, 'Amiwala': 900, 'Huynh': 300,
        }},
        'cook':     {'pct_reporting': 0.55, 'candidates': {
            'Biss': 3800, 'Abughazaleh': 2500, 'Fine': 2700,
            'Simmons': 800, 'Andrew': 1100, 'Amiwala': 700, 'Huynh': 220,
        }},
        'lake':     {'pct_reporting': 0.40, 'candidates': {
            'Biss': 900, 'Abughazaleh': 650, 'Fine': 600,
            'Simmons': 200, 'Andrew': 250, 'Amiwala': 200, 'Huynh': 65,
        }},
        'mchenry':  {'pct_reporting': 0.35, 'candidates': {
            'Biss': 600, 'Abughazaleh': 550, 'Fine': 300,
            'Simmons': 200, 'Andrew': 250, 'Amiwala': 200, 'Huynh': 65,
        }},
    }

    win_prob = {
        'Biss': 0.82, 'Abughazaleh': 0.15, 'Fine': 0.03,
    }

    print('\n--- PHASE 2 THREAD (after thresholds, no winner call yet) ---')
    bot.post_thread(mock_results_phase2, win_prob=win_prob)

    print('\n--- PROJECTED WINNER THREAD ---')
    bot.post_projected_winner('Biss', 97.4, mock_results_phase2)

    print('\n--- ELIMINATION THREAD ---')
    bot.post_elimination('Huynh', mock_results_phase2)