"""
IL-09 Primary Win Probability Simulator (Hybrid Model)
Updated to include:
  - Versioned poll_baseline.json with full history
  - Favorability aware-rate weighting in undecided allocation (pin 1)
  - Second-choice soft constraint for correlated candidate drift (pin 2)
  - Senate district crosstabs passed through to poll_baseline.json
  - Winning simulation snapshots for median-win and closest-win scenario maps
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

N_SIMULATIONS = 1_000_000
PRECINCT_DATA_FILE = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'

# Pin 1 — how much favorability aware-rate blends into undecided weights
# 0.0 = pure crosstab/geographic weights, 1.0 = pure favorability
FAVORABILITY_BLEND = 0.25

# Pin 2 — second-choice soft constraint
# What fraction of a candidate's deviation from baseline routes through
# the transfer matrix rather than floating free as random polling error.
# 0.0 = no constraint (original behavior), 1.0 = fully deterministic transfer
SECOND_CHOICE_CONSTRAINT_STRENGTH = 0.60

# History cutoff — polls before this date form the first history snapshot
HISTORY_CUTOFF_DATE = '2026-01-01'

from poll_config import POLLS, UNDECIDED_ALLOCATION, CANDIDATES, house_effect

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import json
import os


# ============================================================================
# FAVORABILITY WEIGHTING  (Pin 1)
# ============================================================================

def compute_favorability_weights(polls):
    """
    Compute aware-rate favorability weights from the most recent poll
    that contains favorability data.

    aware_fav_rate = favorable / (favorable + unfavorable)
    Normalized to mean of 1.0 across candidates.

    Returns dict {candidate: weight} or {candidate: 1.0} if no fav data.
    """
    fav_polls = sorted(
        [p for p in polls if p.get('favorability')],
        key=lambda p: p['date'],
        reverse=True
    )

    if not fav_polls:
        return {c: 1.0 for c in CANDIDATES}

    poll = fav_polls[0]
    fav_data = poll['favorability']

    print(f"\n  Using favorability from: {poll['name']}")
    print(f"\n  {'Candidate':<16} {'Fav':>6} {'Unfav':>7} {'Aware Rate':>12} {'Weight':>8}")
    print(f"  {'-'*55}")

    raw_rates = {}
    for cand in CANDIDATES:
        if cand not in fav_data:
            raw_rates[cand] = 0.5
            continue
        overall = fav_data[cand].get('overall', {})
        fav = overall.get('favorable', 0)
        unfav = overall.get('unfavorable', 0)
        total_aware = fav + unfav
        raw_rates[cand] = fav / total_aware if total_aware > 0 else 0.5

    mean_rate = np.mean(list(raw_rates.values()))
    weights = {}
    for cand in CANDIDATES:
        weights[cand] = raw_rates[cand] / mean_rate if mean_rate > 0 else 1.0
        fav = fav_data.get(cand, {}).get('overall', {}).get('favorable', 0)
        unfav = fav_data.get(cand, {}).get('overall', {}).get('unfavorable', 0)
        print(f"  {cand:<16} {fav:>5}%  {unfav:>6}%  "
              f"{raw_rates[cand]:>11.1%}  {weights[cand]:>7.3f}x")

    return weights


# ============================================================================
# SECOND-CHOICE MATRIX AGGREGATION  (Pin 2)
# ============================================================================

def aggregate_second_choice_matrix(polls):
    """
    Aggregate second-choice matrices from all polls that have one,
    weighted by recency and poll quality. Returns a normalized
    transfer matrix: {donor: {recipient: probability}}.
    """
    matrix_polls = sorted(
        [p for p in polls if p.get('second_choice_matrix')],
        key=lambda p: p['date'],
        reverse=True
    )

    if not matrix_polls:
        return None

    accumulated = {donor: {recip: 0.0 for recip in CANDIDATES}
                   for donor in CANDIDATES}
    total_weights = {donor: 0.0 for donor in CANDIDATES}

    for poll in matrix_polls:
        weight, _ = calculate_poll_weight(poll)
        scm = poll['second_choice_matrix']

        for donor in CANDIDATES:
            if donor not in scm:
                continue
            choices = scm[donor]
            named = {k: v for k, v in choices.items()
                     if k in CANDIDATES and k != donor}
            total_named = sum(named.values())
            if total_named == 0:
                continue
            for recip, val in named.items():
                accumulated[donor][recip] += (val / total_named) * weight
            total_weights[donor] += weight

    transfer_matrix = {}
    no_second_rates = {}

    for donor in CANDIDATES:
        if total_weights[donor] == 0:
            transfer_matrix[donor] = {r: 1.0 / (len(CANDIDATES) - 1)
                                      for r in CANDIDATES if r != donor}
            no_second_rates[donor] = 0.20
            continue

        raw = {r: accumulated[donor][r] / total_weights[donor]
               for r in CANDIDATES if r != donor}
        total = sum(raw.values())
        transfer_matrix[donor] = ({r: v / total for r, v in raw.items()}
                                   if total > 0 else raw)

        no_second_vals = []
        for poll in matrix_polls:
            scm = poll.get('second_choice_matrix', {})
            if donor in scm:
                choices = scm[donor]
                total_all = sum(choices.values())
                no_s = choices.get('no_second', 0) + choices.get('others', 0)
                if total_all > 0:
                    no_second_vals.append(no_s / total_all)
        no_second_rates[donor] = np.mean(no_second_vals) if no_second_vals else 0.20

    return transfer_matrix, no_second_rates


# ============================================================================
# SENATE DISTRICT CROSSTAB AGGREGATION
# ============================================================================

def aggregate_senate_district_crosstabs(polls):
    sd_polls = sorted(
        [p for p in polls if p.get('senate_district_crosstabs')],
        key=lambda p: p['date'],
        reverse=True
    )

    if not sd_polls:
        return None

    # Always use most recent poll — SD crosstabs shouldn't be averaged across
    # waves since they're a direct geographic snapshot, not a running average
    result = sd_polls[0]['senate_district_crosstabs']
    print(f"\n  Senate district crosstabs from: {sd_polls[0]['name']}")
    for sd_key, sd_data in result.items():
        top = sorted(
            [(c, v) for c, v in sd_data.items() if c in CANDIDATES],
            key=lambda x: -x[1]
        )[:3]
        top_str = ', '.join(f"{c}: {v}%" for c, v in top)
        print(f"    {sd_key}: {top_str} ...")
    return result
    # Multiple polls with SD data — weighted average
    print(f"\n  Aggregating senate district crosstabs from {len(sd_polls)} polls")

    all_sd_keys = set()
    for p in sd_polls:
        all_sd_keys.update(p['senate_district_crosstabs'].keys())

    accumulated = {sd: {c: 0.0 for c in CANDIDATES + ['undecided']}
                   for sd in all_sd_keys}
    total_weights = {sd: 0.0 for sd in all_sd_keys}

    for poll in sd_polls:
        weight, _ = calculate_poll_weight(poll)
        for sd_key, sd_data in poll['senate_district_crosstabs'].items():
            for cand, val in sd_data.items():
                if cand in accumulated[sd_key]:
                    accumulated[sd_key][cand] += val * weight
            total_weights[sd_key] += weight

    result = {}
    for sd_key in all_sd_keys:
        if total_weights[sd_key] > 0:
            result[sd_key] = {
                c: accumulated[sd_key][c] / total_weights[sd_key]
                for c in accumulated[sd_key]
                if accumulated[sd_key][c] > 0
            }

    return result


# ============================================================================
# CROSSTAB PROCESSING
# ============================================================================

def calculate_crosstab_moe(sample_size):
    if sample_size < 30:
        return 20.0
    return (1 / np.sqrt(sample_size)) * 100


def aggregate_crosstabs(polls):
    print("\n" + "=" * 70)
    print("AGGREGATING CROSSTABS")
    print("=" * 70)

    crosstab_polls = [p for p in polls if p.get('has_crosstabs', False)]
    if not crosstab_polls:
        print("No polls with crosstabs available.")
        return None, None

    print(f"Found {len(crosstab_polls)} poll(s) with crosstabs:")
    for poll in crosstab_polls:
        print(f"  - {poll['name']}")

    all_demographics = set()
    for poll in crosstab_polls:
        for cand in CANDIDATES:
            if cand in poll.get('crosstabs', {}):
                all_demographics.update(poll['crosstabs'][cand].keys())

    weighted_crosstabs = {cand: {demo: 0.0 for demo in all_demographics}
                          for cand in CANDIDATES}
    total_weights = {cand: {demo: 0.0 for demo in all_demographics}
                     for cand in CANDIDATES}
    crosstab_moes = {demo: [] for demo in all_demographics}

    for poll in crosstab_polls:
        poll_weight, _ = calculate_poll_weight(poll)
        for cand in CANDIDATES:
            if cand not in poll.get('crosstabs', {}):
                continue
            for demo, pct in poll['crosstabs'][cand].items():
                if pct is None:
                    continue
                sample_size = poll.get('crosstab_sample_sizes', {}).get(
                    demo, poll['sample_size'] * 0.2)
                subsample_weight = np.sqrt(sample_size) / 10
                combined_weight = poll_weight * subsample_weight
                weighted_crosstabs[cand][demo] += pct * combined_weight
                total_weights[cand][demo] += combined_weight
                moe = calculate_crosstab_moe(sample_size)
                crosstab_moes[demo].append(moe)

    averaged_crosstabs = {cand: {} for cand in CANDIDATES}
    for cand in CANDIDATES:
        for demo in all_demographics:
            if total_weights[cand][demo] > 0:
                averaged_crosstabs[cand][demo] = (
                    weighted_crosstabs[cand][demo] / total_weights[cand][demo])
            else:
                averaged_crosstabs[cand][demo] = 0

    avg_demo_moes = {demo: (np.mean(crosstab_moes[demo])
                            if crosstab_moes[demo] else 10.0)
                     for demo in all_demographics}

    print("\nCrosstab Margins of Error by Demographic:")
    print(f"{'Demographic':<20s} {'Avg MOE':<10s} {'Reliability':<15s}")
    print("-" * 50)
    for demo, moe in sorted(avg_demo_moes.items(), key=lambda x: x[1]):
        reliability = "High" if moe < 8 else "Medium" if moe < 12 else "Low"
        print(f"{demo:<20s} ±{moe:>5.1f}%    {reliability:<15s}")

    return averaged_crosstabs, avg_demo_moes


def scale_crosstabs_to_polling_average(averaged_crosstabs, baseline_avg,
                                        crosstab_polls):
    if not averaged_crosstabs:
        return None

    print("\n" + "=" * 70)
    print("SCALING CROSSTABS TO CURRENT POLLING AVERAGE")
    print("=" * 70)

    crosstab_baseline = {}
    total_weight = 0
    for poll in crosstab_polls:
        weight, _ = calculate_poll_weight(poll)
        for cand in CANDIDATES:
            crosstab_baseline[cand] = (crosstab_baseline.get(cand, 0)
                                       + poll['results'].get(cand, 0) * weight)
        total_weight += weight

    for cand in CANDIDATES:
        crosstab_baseline[cand] /= total_weight

    scaled_crosstabs = {cand: {} for cand in CANDIDATES}

    print(f"\n{'Candidate':<15s} {'Crosstab Base':<15s} "
          f"{'Current Avg':<15s} {'Scaling Factor':<15s}")
    print("-" * 70)

    for cand in CANDIDATES:
        original_pct = crosstab_baseline.get(cand, 0)
        current_pct = baseline_avg.get(cand, 0)
        scaling_factor = current_pct / original_pct if original_pct > 0 else 1.0
        print(f"{cand:<15s} {original_pct:>7.1f}%        "
              f"{current_pct:>7.1f}%        {scaling_factor:>7.2f}x")

        for demo, pct in averaged_crosstabs[cand].items():
            if pct < 5:
                scaled_pct = pct * scaling_factor
            elif pct < 15:
                scaled_pct = pct * (scaling_factor ** 0.85)
            else:
                scaled_pct = pct * (scaling_factor ** 0.7)
            scaled_crosstabs[cand][demo] = min(scaled_pct, 95.0)

    return scaled_crosstabs


def map_age_to_crosstab(median_age, crosstabs):
    if median_age < 30:
        return crosstabs.get('age_18-29', 0)
    if median_age >= 65:
        return crosstabs.get('age_65+', 0)
    if 30 <= median_age < 45:
        lower = crosstabs.get('age_30-44', 0)
        upper = crosstabs.get('age_45-65', 0)
        weight = (median_age - 37) / (55 - 37)
    else:
        lower = crosstabs.get('age_45-65', 0)
        upper = crosstabs.get('age_65+', 0)
        weight = (median_age - 55) / (72.5 - 55)
    weight = np.clip(weight, 0, 1)
    return lower * (1 - weight) + upper * weight


# ============================================================================
# PRECINCT BIAS ENGINE
# ============================================================================

def calculate_district_wide_undecided_bias(scaled_crosstabs=None,
                                            fav_weights=None):
    """
    Calculates district-wide undecided bias weights.

    Blends two signals:
      1. Crosstab/geographic weights  — (1 - FAVORABILITY_BLEND)
      2. Favorability aware-rate weights (Pin 1) — FAVORABILITY_BLEND
    """
    print(f"Loading precinct data from {PRECINCT_DATA_FILE}...")
    try:
        df = pd.read_csv(PRECINCT_DATA_FILE)
    except FileNotFoundError:
        print(f"WARNING: {PRECINCT_DATA_FILE} not found. Using neutral weights.")
        return {c: 1.0 for c in CANDIDATES}

    for col in ['prog_score_imputed', 'total_votes_projected', 'undecided_pct']:
        if col not in df.columns:
            df[col] = {'undecided_pct': 0.25,
                       'prog_score_imputed': 0,
                       'total_votes_projected': 500}[col]

    for col, default in [('median_voting_age', 50),
                          ('V_20_VAP_Black_pct', 0.0),
                          ('V_20_VAP_Asian_pct', 0.0)]:
        if col not in df.columns:
            df[col] = default

    prog_scores = df['prog_score_imputed'].dropna()
    moderate_threshold    = prog_scores.quantile(0.333) if len(prog_scores) > 0 else -0.3
    somewhat_lib_threshold = prog_scores.quantile(0.667) if len(prog_scores) > 0 else  0.3

    weighted_counts = {c: 0.0 for c in CANDIDATES}
    total_undecided_mass = 0.0

    if scaled_crosstabs:
        for _, row in df.iterrows():
            n_undecided = (row.get('total_votes_projected', 500)
                           * row.get('undecided_pct', 0.25))
            total_undecided_mass += n_undecided

            prog_score = row.get('prog_score_imputed', 0)
            median_age = row.get('median_voting_age', 50)
            black_pct  = row.get('V_20_VAP_Black_pct', 0)
            asian_pct  = row.get('V_20_VAP_Asian_pct', 0)
            white_pct  = max(0, 100 - black_pct - asian_pct)

            precinct_support = {}
            for cand in CANDIDATES:
                if cand not in scaled_crosstabs:
                    precinct_support[cand] = 1.0
                    continue

                crosstabs = scaled_crosstabs[cand]
                support_components = []

                if prog_score <= moderate_threshold:
                    support_components.append(crosstabs.get('moderate', 0))
                elif prog_score <= somewhat_lib_threshold:
                    support_components.append(crosstabs.get('somewhat_liberal', 0))
                else:
                    support_components.append(crosstabs.get('very_liberal', 0))

                support_components.append(map_age_to_crosstab(median_age, crosstabs))

                white_support = crosstabs.get('white', 0)
                black_support = (crosstabs['black'] if 'black' in crosstabs
                                 else white_support * 3.0 if cand == 'Simmons'
                                 else white_support * 0.8)
                asian_support = (crosstabs['asian'] if 'asian' in crosstabs
                                 else white_support * 2.5 if cand == 'Huynh'
                                 else white_support * 2.0 if cand == 'Amiwala'
                                 else white_support * 0.8)
                racial_support = ((white_pct / 100) * white_support
                                  + (black_pct / 100) * black_support
                                  + (asian_pct / 100) * asian_support)
                support_components.append(racial_support)

                precinct_support[cand] = max(np.mean(support_components), 1.0)

            for cand in CANDIDATES:
                weighted_counts[cand] += n_undecided * precinct_support[cand]

    else:
        for _, row in df.iterrows():
            n_undecided = (row.get('total_votes_projected', 500)
                           * row.get('undecided_pct', 0.25))
            total_undecided_mass += n_undecided
            prog_score = row.get('prog_score_imputed', 0)
            w = {c: 1.0 for c in CANDIDATES}
            if prog_score <= moderate_threshold:
                w['Fine'] *= 1.4; w['Andrew'] *= 1.3
                w['Biss'] *= 0.9; w['Abughazaleh'] *= 0.7
            elif prog_score <= somewhat_lib_threshold:
                w['Biss'] *= 1.3; w['Abughazaleh'] *= 1.1
            else:
                w['Abughazaleh'] *= 1.4; w['Simmons'] *= 1.3
                w['Amiwala'] *= 1.2; w['Fine'] *= 0.7
            for cand in CANDIDATES:
                weighted_counts[cand] += n_undecided * w[cand]

    if total_undecided_mass > 0:
        avg_weights = {c: weighted_counts[c] / total_undecided_mass
                       for c in CANDIDATES}
        mean_weight = np.mean(list(avg_weights.values()))
        geo_weights = ({c: avg_weights[c] / mean_weight for c in CANDIDATES}
                       if mean_weight > 0 else {c: 1.0 for c in CANDIDATES})
    else:
        geo_weights = {c: 1.0 for c in CANDIDATES}

    if fav_weights is None:
        fav_weights = {c: 1.0 for c in CANDIDATES}

    final_weights = {
        cand: ((1.0 - FAVORABILITY_BLEND) * geo_weights[cand]
               + FAVORABILITY_BLEND * fav_weights[cand])
        for cand in CANDIDATES
    }

    mean_final = np.mean(list(final_weights.values()))
    if mean_final > 0:
        final_weights = {c: final_weights[c] / mean_final for c in CANDIDATES}

    print(f"\n  Undecided weights (geo {1-FAVORABILITY_BLEND:.0%} / "
          f"fav {FAVORABILITY_BLEND:.0%} blend):")
    for cand in CANDIDATES:
        geo   = geo_weights.get(cand, 1.0)
        fav   = fav_weights.get(cand, 1.0)
        final = final_weights[cand]
        print(f"    {cand:<16}: geo={geo:.3f}x  fav={fav:.3f}x  "
              f"→ final={final:.3f}x")

    return final_weights


# ============================================================================
# CORE SIMULATION FUNCTIONS
# ============================================================================

def calculate_margin_of_error(sample_size):
    return (1 / np.sqrt(sample_size)) * 100


def apply_house_effect(poll):
    if not poll.get('is_internal', False):
        return poll['results'].copy(), poll.get('undecided', 0)
    internal_candidate = poll.get('internal_for')
    adjustment = poll.get('house_effect_adjustment', 0)
    if not internal_candidate or adjustment == 0:
        return poll['results'].copy(), poll.get('undecided', 0)
    adjusted_results = poll['results'].copy()
    current_undecided = poll.get('undecided', 0)
    if internal_candidate in adjusted_results:
        adjusted_results[internal_candidate] = max(
            0, adjusted_results[internal_candidate] - adjustment)
        new_undecided = current_undecided + adjustment
    else:
        new_undecided = current_undecided
    return adjusted_results, new_undecided


def compute_trend_signal(polls, decay_half_life_days=30):
    polls_sorted = sorted(polls, key=lambda p: p['date'])
    last_by_pollster = {}
    trend_raw = {}
    pollster_count = set()
    for poll in polls_sorted:
        pollster_id = poll.get('pollster_id', 'Unknown')
        poll_date = datetime.strptime(poll['date'], '%Y-%m-%d')
        if pollster_id in last_by_pollster:
            prev_poll, prev_date = last_by_pollster[pollster_id]
            days_diff = (poll_date - prev_date).days
            decay = 0.5 ** (days_diff / decay_half_life_days)
            internal_discount = 0.5 if poll.get('is_internal') else 1.0
            for cand, pct in poll['results'].items():
                prev_pct = prev_poll['results'].get(cand)
                if prev_pct is not None:
                    delta = (pct - prev_pct) * decay * internal_discount
                    trend_raw[cand] = trend_raw.get(cand, 0) + delta
            pollster_count.add(pollster_id)
        last_by_pollster[pollster_id] = (poll, poll_date)
    diversity_multiplier = 1.0 if len(pollster_count) > 1 else 0.4
    if trend_raw:
        max_abs = max(abs(v) for v in trend_raw.values()) or 1
        return {cand: (trend_raw.get(cand, 0) / max_abs) * diversity_multiplier
                for cand in trend_raw}
    return {}


def calculate_poll_weight(poll):
    quality_weight = poll['pollster_quality']
    moe = poll.get('margin_of_error',
                   calculate_margin_of_error(poll['sample_size']))
    moe_weight = 100 / moe
    poll_date = datetime.strptime(poll['date'], '%Y-%m-%d')
    days_old = (datetime.now() - poll_date).days
    recency_weight = (1.0 if days_old <= 7
                      else 0.5 ** ((days_old - 7) / 14))
    internal_penalty = 0.5 if poll.get('is_internal', False) else 1.0
    return quality_weight * moe_weight * recency_weight * internal_penalty, moe


def aggregate_polls(polls):
    candidates = CANDIDATES + ['Others']
    poll_weights = []
    adjusted_polls = []
    adjusted_undecideds = []

    for poll in polls:
        adjusted_results, adjusted_undecided = apply_house_effect(poll)
        adjusted_poll = poll.copy()
        adjusted_poll['results'] = adjusted_results
        adjusted_polls.append(adjusted_poll)
        adjusted_undecideds.append(adjusted_undecided)
        weight, moe = calculate_poll_weight(poll)
        poll_weights.append(weight)

    total_weight = sum(poll_weights)
    weighted_results = {}
    for cand in candidates:
        weighted_sum = sum(poll['results'].get(cand, 0) * weight
                           for poll, weight in zip(adjusted_polls, poll_weights))
        weighted_results[cand] = weighted_sum / total_weight

    total_named = sum(weighted_results[c] for c in candidates if c != 'Others')
    undecided = (sum(u * w for u, w in zip(adjusted_undecideds, poll_weights))
                 / total_weight)
    weighted_results['Others'] = max(0, 100 - total_named - undecided)

    return weighted_results, undecided


def calculate_average_moe(polls):
    weights = []
    moes = []
    for poll in polls:
        weight, moe = calculate_poll_weight(poll)
        weights.append(weight)
        moes.append(moe)
    return sum(m * w for m, w in zip(moes, weights)) / sum(weights)


def allocate_smart_undecideds(undecided_pct, baseline, composite_weights):
    candidates = [c for c in baseline.keys() if c != 'Others']
    allocation = {c: 0.0 for c in candidates}
    weighted_shares = {}
    total_share = 0
    for cand in candidates:
        share = baseline.get(cand, 0) * composite_weights.get(cand, 1.0)
        weighted_shares[cand] = share
        total_share += share
    if total_share == 0:
        return allocation
    for cand in candidates:
        allocation[cand] = undecided_pct * (weighted_shares[cand] / total_share)
    return allocation


def simulate_election(baseline, undecided_pct, avg_moe, trend_signal,
                       composite_weights, transfer_matrix=None,
                       no_second_rates=None):
    """
    Runs one election simulation.

    Pin 2: If transfer_matrix is provided, candidate deviations from baseline
    are partially routed through second-choice transfers rather than floating
    free. SECOND_CHOICE_CONSTRAINT_STRENGTH controls the fraction.
    """
    candidates = CANDIDATES
    results = {}
    PRIMARY_VOLATILITY = 2.75
    TREND_STRENGTH = 0.15
    TREND_NOISE = 0.3

    # 1. Draw raw errors
    for cand in candidates:
        trend_effect = trend_signal.get(cand, 0) * TREND_STRENGTH * avg_moe
        trend_noise  = np.random.normal(0, TREND_NOISE * avg_moe)
        error        = np.random.normal(0, avg_moe * 0.5 * PRIMARY_VOLATILITY)
        results[cand] = max(0, baseline.get(cand, 0) + error + trend_effect + trend_noise)

    # 2. Pin 2 — Second-choice soft constraint
    if transfer_matrix and no_second_rates:
        transfer_adjustments = {c: 0.0 for c in candidates}

        for donor in candidates:
            deviation = results[donor] - baseline.get(donor, 0)
            if deviation >= 0:
                continue
            loss = abs(deviation)
            constrained_loss = loss * SECOND_CHOICE_CONSTRAINT_STRENGTH
            transfer_adjustments[donor] += constrained_loss

            probs = transfer_matrix.get(donor, {})
            no_second = no_second_rates.get(donor, 0.20)
            transferable_share = 1.0 - no_second
            active_recipients = {r: p for r, p in probs.items()
                                  if r in candidates and r != donor}
            active_total = sum(active_recipients.values())

            if active_total > 0:
                for recip, prob in active_recipients.items():
                    transfer_adjustments[recip] -= (
                        constrained_loss * transferable_share
                        * (prob / active_total)
                    )

        for cand in candidates:
            results[cand] = max(0, results[cand] - transfer_adjustments[cand])

    # 3. Breakout events
    if np.random.rand() < 0.05:
        eligible = [c for c in candidates if results[c] < 15]
        if eligible:
            results[np.random.choice(eligible)] += np.random.uniform(3, 7)

    undecided_votes = undecided_pct

    # 4. Late surge breakout
    if np.random.rand() < 0.25:
        results['Other_Breakout'] = np.random.uniform(0.3, 0.7) * undecided_pct

    # 5. Smart undecided allocation
    smart_allocation = allocate_smart_undecideds(
        undecided_votes * UNDECIDED_ALLOCATION['proportional'],
        baseline, composite_weights
    )
    for cand, votes in smart_allocation.items():
        if cand in results:
            results[cand] += votes

    # 6. Bandwagon effect
    sorted_cands = sorted(results.items(), key=lambda x: x[1], reverse=True)
    top_3 = [c for c, v in sorted_cands[:3]]
    top_total = sum(results[c] for c in top_3)
    if top_total > 0:
        for cand in top_3:
            results[cand] += ((results[cand] / top_total)
                              * (undecided_votes * UNDECIDED_ALLOCATION['top_candidates']))

    # 7. Random noise
    for cand in candidates:
        results[cand] += np.random.uniform(
            0,
            (undecided_votes * UNDECIDED_ALLOCATION['random']) / len(candidates) * 2
        )

    # Normalize
    total = sum(results.values())
    if total > 0:
        for cand in results:
            results[cand] = (results[cand] / total) * 100

    return results


# ============================================================================
# MONTE CARLO
# ============================================================================

def run_monte_carlo(polls, n_simulations=N_SIMULATIONS):
    print("=" * 70)
    print("MONTE CARLO WIN PROBABILITY SIMULATION")
    print("=" * 70)

    baseline, undecided_pct = aggregate_polls(polls)
    avg_moe = calculate_average_moe(polls)
    trend_signal = compute_trend_signal(polls)

    # Crosstabs
    crosstab_polls = [p for p in polls if p.get('has_crosstabs', False)]
    averaged_crosstabs = scaled_crosstabs = crosstab_moes = None
    if crosstab_polls:
        averaged_crosstabs, crosstab_moes = aggregate_crosstabs(polls)
        if averaged_crosstabs:
            scaled_crosstabs = scale_crosstabs_to_polling_average(
                averaged_crosstabs, baseline, crosstab_polls)
            print_crosstab_summary(scaled_crosstabs)

    # Pin 1 — Favorability weights
    print("\n" + "=" * 70)
    print("FAVORABILITY AWARE-RATE WEIGHTS  (Pin 1)")
    print("=" * 70)
    fav_weights = compute_favorability_weights(polls)

    # Pin 2 — Second-choice transfer matrix
    print("\n" + "=" * 70)
    print("SECOND-CHOICE TRANSFER MATRIX  (Pin 2)")
    print("=" * 70)
    sc_result = aggregate_second_choice_matrix(polls)
    if sc_result:
        transfer_matrix, no_second_rates = sc_result
        print(f"  Transfer matrix built from "
              f"{len([p for p in polls if p.get('second_choice_matrix')])} poll(s)")
        print(f"  Constraint strength: {SECOND_CHOICE_CONSTRAINT_STRENGTH:.0%} "
              f"of downward deviations routed through transfers")
    else:
        transfer_matrix = no_second_rates = None
        print("  No second-choice data available — constraint disabled")

    # Senate district crosstabs
    print("\n" + "=" * 70)
    print("SENATE DISTRICT CROSSTABS")
    print("=" * 70)
    senate_crosstabs = aggregate_senate_district_crosstabs(polls)
    if senate_crosstabs:
        print(f"  ✓ Senate district crosstabs aggregated for {list(senate_crosstabs.keys())}")
    else:
        print("  ⚠ No senate district crosstabs found in any poll")

    # Composite undecided weights
    print("\n" + "=" * 70)
    print("COMPOSITE UNDECIDED WEIGHTS")
    print("=" * 70)
    composite_weights = calculate_district_wide_undecided_bias(
        scaled_crosstabs, fav_weights)

    # Baseline printout
    print("\nBASELINE: WEIGHTED POLL AVERAGE")
    print("-" * 70)
    for cand in CANDIDATES:
        print(f"  {cand:15s}: {baseline.get(cand, 0):5.1f}%")
    print(f"\n  Undecided: {undecided_pct:.1f}%")
    print(f"  Average MOE: ±{avg_moe:.1f}%")
    print("-" * 70)

    tracking_candidates = CANDIDATES + ['Other_Breakout']
    wins               = {cand: 0   for cand in tracking_candidates}
    all_results        = {cand: []  for cand in tracking_candidates}
    best_scenarios     = {cand: 0.0 for cand in CANDIDATES}

    # NEW: store the full result snapshot for every simulation a candidate wins.
    # Keyed by winner; each entry is a dict {candidate: normalised_vote_share}.
    # Only CANDIDATES (not Other_Breakout) are stored — these snapshots feed
    # directly into the precinct scenario pipeline as calibration baselines.
    winning_simulations = {cand: [] for cand in CANDIDATES}

    print(f"\nRunning {n_simulations:,} simulations...")

    for i in range(n_simulations):
        if (i + 1) % 50000 == 0:
            print(f"  Completed {i+1:,}/{n_simulations:,}...")

        results = simulate_election(
            baseline, undecided_pct, avg_moe, trend_signal,
            composite_weights, transfer_matrix, no_second_rates
        )
        winner = max(results.items(), key=lambda x: x[1])[0]
        if winner not in wins:
            wins[winner] = 0
            all_results[winner] = [0] * i
        wins[winner] += 1

        # NEW: store snapshot for median-win / closest-win scenario analysis.
        # Only store for the 7 main candidates (winner in winning_simulations
        # means they are a named candidate, not Other_Breakout).
        if winner in winning_simulations:
            winning_simulations[winner].append(
                {c: results.get(c, 0.0) for c in CANDIDATES}
            )

        for cand, score in results.items():
            if cand in best_scenarios and score > best_scenarios[cand]:
                best_scenarios[cand] = score

        for cand in tracking_candidates:
            all_results[cand].append(results.get(cand, 0))

    win_probs = {c: (wins[c] / n_simulations) * 100 for c in CANDIDATES}
    percentiles = {
        c: {p: np.percentile(all_results[c], q)
            for p, q in zip(['p10', 'p25', 'p50', 'p75', 'p90'],
                            [10, 25, 50, 75, 90])}
        for c in CANDIDATES
    }

    # NEW: included in return tuple so main() can export win_scenarios.json
    return (win_probs, percentiles, all_results, wins, best_scenarios,
            scaled_crosstabs, crosstab_moes, fav_weights,
            transfer_matrix, no_second_rates, senate_crosstabs,
            winning_simulations)


# ============================================================================
# WIN SCENARIO COMPUTATION AND EXPORT
# ============================================================================

def compute_and_export_win_scenarios(winning_simulations,
                                      output_path='win_scenarios.json'):
    """
    For each candidate compute two scenario snapshots from their winning sims:

      median_win   — 50th-percentile world across all simulations they won.
                     Represents a "typical" winning outcome.

      closest_win  — the single simulation where their margin over the runner-up
                     was smallest.  Represents a squeaker / stress-test scenario.

    Each scenario stores a full 7-candidate vote-share dict (normalised to 100)
    so it can be dropped directly into the precinct pipeline as a baseline.

    Saves win_scenarios.json and returns the output dict.
    """
    print("\n" + "=" * 70)
    print("WIN SCENARIO ANALYSIS")
    print("=" * 70)

    scenarios = {}

    for cand in CANDIDATES:
        sims = winning_simulations.get(cand, [])

        if not sims:
            print(f"  {cand:<16}: 0 winning simulations — skipping")
            scenarios[cand] = None
            continue

        print(f"  {cand:<16}: {len(sims):,} winning simulations")

        # ── Median win scenario ───────────────────────────────────────────
        # Take the per-candidate median across all winning snapshots, then
        # re-normalise so shares sum to 100.
        raw_medians = {c: float(np.median([s[c] for s in sims])) for c in CANDIDATES}
        total_med   = sum(raw_medians.values())
        median_shares = {c: round(raw_medians[c] / total_med * 100, 3)
                         for c in CANDIDATES}
        median_margin = median_shares[cand] - max(
            v for c, v in median_shares.items() if c != cand
        )

        # ── Closest win scenario ──────────────────────────────────────────
        # Find the single snapshot with the smallest winner's margin.
        def _margin(s):
            total = sum(s.values())
            if total == 0:
                return 0.0
            normed = {c: s[c] / total * 100 for c in CANDIDATES}
            return normed[cand] - max(v for c, v in normed.items() if c != cand)

        closest_sim    = min(sims, key=_margin)
        closest_total  = sum(closest_sim.values())
        closest_shares = {c: round(closest_sim[c] / closest_total * 100, 3)
                          for c in CANDIDATES}
        closest_margin = closest_shares[cand] - max(
            v for c, v in closest_shares.items() if c != cand
        )

        scenarios[cand] = {
            'n_winning_sims': len(sims),
            'median_win': {
                'vote_shares':    median_shares,
                'winner_margin':  round(median_margin, 3),
            },
            'closest_win': {
                'vote_shares':    closest_shares,
                'winner_margin':  round(closest_margin, 3),
            },
        }

    # ── Print summary table ───────────────────────────────────────────────
    print(f"\n{'Candidate':<16} {'Win Sims':>10} {'Med Win Margin':>16} "
          f"{'Closest Win Margin':>20}")
    print("-" * 68)
    for cand in CANDIDATES:
        s = scenarios.get(cand)
        if s is None:
            print(f"  {cand:<14} {'—':>10}")
            continue
        print(f"  {cand:<14} {s['n_winning_sims']:>10,} "
              f"{s['median_win']['winner_margin']:>15.2f}% "
              f"{s['closest_win']['winner_margin']:>19.2f}%")

    output = {
        'generated_at': datetime.now().isoformat(),
        'n_simulations': N_SIMULATIONS,
        'scenarios': scenarios,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\n✓ win_scenarios.json written → {output_path}")
    return output


# ============================================================================
# VERSIONED POLL BASELINE HISTORY
# ============================================================================

def build_poll_history(all_polls, n_simulations_history=100_000):
    """
    Builds a chronological list of polling snapshots.
    Each snapshot contains baseline, crosstabs, favorability, second-choice,
    senate district crosstabs, and win probabilities at that point in time.
    """
    print("\n" + "=" * 70)
    print("BUILDING VERSIONED POLL HISTORY")
    print("=" * 70)

    cutoff = datetime.strptime(HISTORY_CUTOFF_DATE, '%Y-%m-%d')
    sorted_polls = sorted(all_polls, key=lambda p: p['date'])

    snapshot_definitions = []

    pre_cutoff = [p for p in sorted_polls
                  if datetime.strptime(p['date'], '%Y-%m-%d') < cutoff]
    if pre_cutoff:
        snapshot_definitions.append({
            'as_of': HISTORY_CUTOFF_DATE,
            'label': 'pre_2026_cutoff',
            'polls': pre_cutoff,
            'trigger_poll': None
        })

    seen_dates = set()
    for poll in sorted_polls:
        date_str = poll['date']
        if date_str in seen_dates:
            continue
        seen_dates.add(date_str)
        polls_up_to = [p for p in sorted_polls if p['date'] <= date_str]
        poll_name = (poll['name'].lower()
                     .replace(' ', '_').replace('/', '_')
                     .replace('(', '').replace(')', ''))
        snapshot_definitions.append({
            'as_of': date_str,
            'label': f"after_{poll_name}_{date_str}",
            'polls': polls_up_to,
            'trigger_poll': poll['name']
        })

    history = []

    for snap_def in snapshot_definitions:
        as_of      = snap_def['as_of']
        label      = snap_def['label']
        snap_polls = snap_def['polls']
        trigger    = snap_def['trigger_poll']

        print(f"\n  Building snapshot: {label}")
        print(f"    Polls included: {len(snap_polls)}")

        if not snap_polls:
            continue

        try:
            baseline, undecided_pct = aggregate_polls(snap_polls)
            avg_moe = calculate_average_moe(snap_polls)
            trend_signal = compute_trend_signal(snap_polls)

            crosstab_polls = [p for p in snap_polls if p.get('has_crosstabs')]
            scaled_crosstabs = crosstab_moes = None
            if crosstab_polls:
                averaged_crosstabs, crosstab_moes = aggregate_crosstabs(snap_polls)
                if averaged_crosstabs:
                    scaled_crosstabs = scale_crosstabs_to_polling_average(
                        averaged_crosstabs, baseline, crosstab_polls)

            fav_weights = compute_favorability_weights(snap_polls)

            sc_result = aggregate_second_choice_matrix(snap_polls)
            transfer_matrix_json  = sc_result[0] if sc_result else None
            no_second_rates_json  = sc_result[1] if sc_result else None

            senate_crosstabs_snap = aggregate_senate_district_crosstabs(snap_polls)

            sc_topline  = _aggregate_second_choice_topline(snap_polls)
            fav_topline = _aggregate_favorability_topline(snap_polls)

            composite_weights = calculate_district_wide_undecided_bias(
                scaled_crosstabs, fav_weights)

            wins_snap    = {c: 0  for c in CANDIDATES}
            all_res_snap = {c: [] for c in CANDIDATES}

            for _ in range(n_simulations_history):
                res = simulate_election(
                    baseline, undecided_pct, avg_moe, trend_signal,
                    composite_weights, transfer_matrix_json, no_second_rates_json
                )
                winner = max({c: res[c] for c in CANDIDATES}.items(),
                             key=lambda x: x[1])[0]
                wins_snap[winner] += 1
                for c in CANDIDATES:
                    all_res_snap[c].append(res.get(c, 0))

            win_probs_snap = {c: (wins_snap[c] / n_simulations_history) * 100
                              for c in CANDIDATES}
            median_snap    = {c: float(np.median(all_res_snap[c]))
                              for c in CANDIDATES}

            snapshot = {
                'as_of': as_of,
                'label': label,
                'trigger_poll': trigger,
                'n_polls_included': len(snap_polls),
                'poll_names': [p['name'] for p in snap_polls],
                'baseline': {k: v for k, v in baseline.items() if k in CANDIDATES},
                'median_forecast': median_snap,
                'win_probabilities': win_probs_snap,
                'undecided_pct': undecided_pct,
                'avg_moe': avg_moe,
                'scaled_crosstabs': scaled_crosstabs,
                'crosstab_moes': crosstab_moes,
                'senate_district_crosstabs': senate_crosstabs_snap,
                'favorability_weights': fav_weights,
                'favorability_topline': fav_topline,
                'second_choice_topline': sc_topline,
                'second_choice_transfer_matrix': transfer_matrix_json,
                'second_choice_no_second_rates': no_second_rates_json,
            }

            history.append(snapshot)
            print(f"    ✓ Win probs: "
                  + ", ".join(f"{c}: {win_probs_snap[c]:.1f}%"
                               for c in sorted(CANDIDATES,
                                               key=lambda x: -win_probs_snap[x])[:3])
                  + "...")

        except Exception as e:
            print(f"    ✗ Error building snapshot {label}: {e}")
            import traceback; traceback.print_exc()
            continue

    return history


def _aggregate_second_choice_topline(polls):
    sc_polls = [p for p in polls if p.get('second_choice')]
    if not sc_polls:
        return None
    accumulated = {c: 0.0 for c in CANDIDATES + ['no_second', 'Others']}
    total_weight = 0.0
    for poll in sc_polls:
        weight, _ = calculate_poll_weight(poll)
        sc = poll['second_choice']
        for key in accumulated:
            accumulated[key] += sc.get(key, 0) * weight
        total_weight += weight
    if total_weight == 0:
        return None
    return {k: v / total_weight for k, v in accumulated.items()}


def _aggregate_favorability_topline(polls):
    fav_polls = [p for p in polls if p.get('favorability')]
    if not fav_polls:
        return None
    accumulated = {
        c: {'favorable': 0.0, 'unfavorable': 0.0,
            'not_heard': 0.0, 'not_sure': 0.0}
        for c in CANDIDATES
    }
    total_weight = 0.0
    for poll in fav_polls:
        weight, _ = calculate_poll_weight(poll)
        fav_data = poll['favorability']
        for cand in CANDIDATES:
            if cand not in fav_data:
                continue
            overall = fav_data[cand].get('overall', {})
            for key in ['favorable', 'unfavorable', 'not_heard', 'not_sure']:
                accumulated[cand][key] += overall.get(key, 0) * weight
        total_weight += weight
    if total_weight == 0:
        return None
    result = {}
    for cand in CANDIDATES:
        avg = {k: v / total_weight for k, v in accumulated[cand].items()}
        fav   = avg['favorable']
        unfav = avg['unfavorable']
        aware_total = fav + unfav
        avg['net'] = fav - unfav
        avg['aware_fav_rate'] = (fav / aware_total * 100) if aware_total > 0 else 50.0
        result[cand] = avg
    return result


# ============================================================================
# DISPLAY / PRINT HELPERS
# ============================================================================

def display_win_counts(wins, n_simulations):
    print("\n" + "=" * 70)
    print(f"RAW WIN COUNTS (Out of {n_simulations:,} Simulations)")
    print("=" * 70)
    for cand, count in sorted(wins.items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            print(f"{cand:<20s} {count:<15,}")


def print_best_scenarios(best_scenarios):
    print("\n" + "=" * 70)
    print("CEILING ANALYSIS: BEST POSSIBLE OUTCOMES")
    print("=" * 70)
    for cand, high in sorted(best_scenarios.items(), key=lambda x: x[1], reverse=True):
        print(f"  {cand:15s}: {high:5.1f}%")


def display_results(win_probs, percentiles):
    print("\n" + "=" * 70)
    print("WIN PROBABILITIES")
    print("=" * 70)
    print(f"\n{'Candidate':<15s} {'Win Prob':<12s} {'Likely Range (50%)':<25s}")
    print("-" * 70)
    for cand, prob in sorted(win_probs.items(), key=lambda x: x[1], reverse=True):
        p25 = percentiles[cand]['p25']
        p75 = percentiles[cand]['p75']
        p50 = percentiles[cand]['p50']
        bar = "█" * int(prob / 2)
        print(f"{cand:<15s} {prob:>5.1f}%  {bar:<25s} "
              f"{p25:.1f}%-{p75:.1f}% (median: {p50:.1f}%)")


def create_visualization(win_probs, percentiles, all_results):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    sorted_probs = sorted(win_probs.items(), key=lambda x: x[1], reverse=True)
    cands, probs = zip(*sorted_probs)
    ax1.barh(cands, probs, color='skyblue')
    ax1.set_title('Win Probability (%)')
    ax2.boxplot([all_results[c] for c in cands if c in all_results],
                labels=[c for c in cands if c in all_results], vert=False)
    ax2.set_title('Distribution of Outcomes')
    plt.tight_layout()
    plt.savefig('win_probabilities.png')
    plt.close()


def print_crosstab_summary(scaled_crosstabs):
    if not scaled_crosstabs:
        print("\nNo crosstabs available to display.")
        return
    print("\n" + "=" * 70)
    print("SCALED CROSSTABS - DEMOGRAPHIC SUPPORT PROFILES")
    print("=" * 70)

    all_demographics = set()
    for ct in scaled_crosstabs.values():
        all_demographics.update(ct.keys())

    ideology_demos = sorted([d for d in all_demographics
                              if 'liberal' in d or 'moderate' in d])
    age_demos  = sorted([d for d in all_demographics if 'age' in d])
    race_demos = [d for d in all_demographics
                  if d in ['white', 'black', 'asian', 'hispanic']]

    if ideology_demos:
        print("\nIDEOLOGY:")
        print(f"{'Candidate':<15s} {'Moderate':<12s} "
              f"{'Smwt Liberal':<15s} {'Very Liberal':<15s}")
        print("-" * 60)
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                mod  = scaled_crosstabs[cand].get('moderate', 0)
                smwt = scaled_crosstabs[cand].get('somewhat_liberal', 0)
                very = scaled_crosstabs[cand].get('very_liberal', 0)
                print(f"{cand:<15s} {mod:>7.1f}%      "
                      f"{smwt:>7.1f}%         {very:>7.1f}%")

    if age_demos:
        print("\nAGE:")
        header = f"{'Candidate':<15s}" + "".join(f" {d:<12s}" for d in age_demos)
        print(header)
        print("-" * (15 + 13 * len(age_demos)))
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                row = f"{cand:<15s}"
                for demo in age_demos:
                    val = scaled_crosstabs[cand].get(demo, 0)
                    row += f" {val:>7.1f}%    "
                print(row)

    if race_demos:
        print("\nRACE/ETHNICITY:")
        header = f"{'Candidate':<15s}" + "".join(f" {d.capitalize():<12s}" for d in race_demos)
        print(header)
        print("-" * (15 + 13 * len(race_demos)))
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                row = f"{cand:<15s}"
                for demo in race_demos:
                    val = scaled_crosstabs[cand].get(demo, 0)
                    row += f" {val:>7.1f}%    "
                print(row)

    print("\n" + "=" * 70)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(POLLS) == 0:
        print("\nERROR: No polls configured!")
        exit(1)

    # -----------------------------------------------------------------------
    # PRIMARY SIMULATION (full N_SIMULATIONS, all polls)
    # -----------------------------------------------------------------------
    (win_probs, percentiles, all_results, wins, best_scenarios,
     scaled_crosstabs, crosstab_moes, fav_weights,
     transfer_matrix, no_second_rates,
     senate_crosstabs,
     winning_simulations) = run_monte_carlo(POLLS, N_SIMULATIONS)   # ← unpacks new value

    display_win_counts(wins, N_SIMULATIONS)
    display_results(win_probs, percentiles)
    print_best_scenarios(best_scenarios)
    print_crosstab_summary(scaled_crosstabs)
    create_visualization(win_probs, percentiles, all_results)

    # NEW: compute median-win and closest-win scenarios, write win_scenarios.json
    compute_and_export_win_scenarios(winning_simulations)

    # -----------------------------------------------------------------------
    # EXPORT — build full versioned history
    # -----------------------------------------------------------------------
    baseline, undecided_pct = aggregate_polls(POLLS)
    avg_moe = calculate_average_moe(POLLS)
    median_forecast = {c: float(np.percentile(all_results[c], 50))
                       for c in CANDIDATES}

    fav_topline = _aggregate_favorability_topline(POLLS)
    sc_topline  = _aggregate_second_choice_topline(POLLS)
    sc_result   = aggregate_second_choice_matrix(POLLS)
    transfer_matrix_export = sc_result[0] if sc_result else None
    no_second_export       = sc_result[1] if sc_result else None

    print("\n" + "=" * 70)
    print("BUILDING POLL HISTORY SNAPSHOTS")
    print("(100k sims per snapshot — this may take a few minutes)")
    print("=" * 70)
    history = build_poll_history(POLLS, n_simulations_history=100_000)

    # -----------------------------------------------------------------------
    # Load previous results for change tracking
    # -----------------------------------------------------------------------
    old_data = {}
    if os.path.exists('district_win_probabilities.json'):
        with open('district_win_probabilities.json', 'r') as f:
            old_data = json.load(f)

    changes = {
        c: {
            'win_prob_change': (win_probs[c]
                                - old_data.get('win_probabilities', {})
                                .get(c, win_probs[c])),
            'vote_share_change': (median_forecast[c]
                                  - old_data.get('median_results', {})
                                  .get(c, median_forecast[c]))
        }
        for c in CANDIDATES
    }

    last_run = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    # -----------------------------------------------------------------------
    # Write poll_baseline.json  (versioned)
    # -----------------------------------------------------------------------
    poll_baseline_out = {
        # Current snapshot — what all downstream scripts consume
        'current': {
            'as_of': max(p['date'] for p in POLLS),
            'baseline': {k: v for k, v in baseline.items() if k in CANDIDATES},
            'median_forecast': median_forecast,
            'undecided_pct': undecided_pct,
            'avg_moe': avg_moe,
            'scaled_crosstabs': scaled_crosstabs,
            'crosstab_moes': crosstab_moes,
            # Pin 1
            'favorability_weights': fav_weights,
            'favorability_topline': fav_topline,
            # Pin 2
            'second_choice_topline': sc_topline,
            'second_choice_transfer_matrix': transfer_matrix_export,
            'second_choice_no_second_rates': no_second_export,
            # Senate district crosstabs — consumed by win_probability_precinct.py
            # via ['current']['senate_district_crosstabs']
            'senate_district_crosstabs': senate_crosstabs,
        },

        # Full chronological history
        'history': history,

        # Banked votes placeholder — populated by precinct map script
        'banked_votes': {c: 0 for c in CANDIDATES},

        'last_run': last_run,
        'n_simulations': N_SIMULATIONS,
    }

    with open('poll_baseline.json', 'w') as f:
        json.dump(poll_baseline_out, f, indent=2)

    print(f"\n✓ poll_baseline.json written with {len(history)} history snapshots")
    if senate_crosstabs:
        print(f"✓ senate_district_crosstabs included: {list(senate_crosstabs.keys())}")
    else:
        print("⚠ senate_district_crosstabs: None (no poll had senate district data)")

    # -----------------------------------------------------------------------
    # Write district_win_probabilities.json
    # -----------------------------------------------------------------------
    new_dist_data = {
        'win_probabilities': win_probs,
        'median_results': median_forecast,
        'simulation_wins': wins,
        'last_run': last_run,
        'changes': changes,
    }
    if old_data.get('win_probabilities'):
        new_dist_data['win_probabilities_old'] = old_data['win_probabilities']
    if old_data.get('median_results'):
        new_dist_data['median_results_old'] = old_data['median_results']

    with open('district_win_probabilities.json', 'w') as f:
        json.dump(new_dist_data, f, indent=2)

    # -----------------------------------------------------------------------
    # Print changes since last run
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("CHANGES SINCE LAST RUN")
    print("=" * 70)
    if old_data.get('win_probabilities'):
        print(f"\n{'Candidate':<15s} {'Win Prob Change':<20s} "
              f"{'Vote Share Change':<20s}")
        print("-" * 60)
        for cand in CANDIDATES:
            wp_change = changes[cand]['win_prob_change']
            vs_change = changes[cand]['vote_share_change']
            wp_arrow  = "↑" if wp_change > 0 else "↓" if wp_change < 0 else "→"
            vs_arrow  = "↑" if vs_change > 0 else "↓" if vs_change < 0 else "→"
            print(f"{cand:<15s} {wp_arrow} {wp_change:+6.1f}%           "
                  f"{vs_arrow} {vs_change:+6.1f}%")
    else:
        print("No previous run to compare against.")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE!")
    print("=" * 70)
    print(f"\nOutputs:")
    print(f"  poll_baseline.json              — versioned history + current snapshot")
    print(f"  district_win_probabilities.json — win probs for map")
    print(f"  win_scenarios.json              — median-win + closest-win per candidate")
    print(f"  win_probabilities.png           — visualization")
    print(f"\nHistory snapshots: {len(history)}")
    for snap in history:
        print(f"  {snap['as_of']}  {snap['label'][:55]}")