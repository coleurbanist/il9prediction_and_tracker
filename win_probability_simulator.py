"""
IL-09 Primary Win Probability Simulator (Hybrid Model)

This script calculates a geographically weighted undecided bias based on
precinct-level data, then runs Monte Carlo simulations to estimate each
candidate's probability of winning.
"""

# ============================================================================
# CONFIGURATION
# ============================================================================

N_SIMULATIONS = 1000000  # Number of elections to simulate
PRECINCT_DATA_FILE = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'

# PULL DATA FROM THE CENTRAL FILE
from poll_config import POLLS, UNDECIDED_ALLOCATION, CANDIDATES, house_effect

# ============================================================================
# CROSSTAB PROCESSING
# ============================================================================

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt
import json


def calculate_crosstab_moe(sample_size):
    """Calculate margin of error for crosstab subgroups"""
    if sample_size < 30:
        return 20.0  # Very unreliable
    return (1 / np.sqrt(sample_size)) * 100


def aggregate_crosstabs(polls):
    """
    Aggregate crosstabs across polls, weighted by recency, quality, and sample size.
    Returns averaged crosstabs scaled to current polling average.
    """
    print("\n" + "=" * 70)
    print("AGGREGATING CROSSTABS")
    print("=" * 70)

    # Find polls with crosstabs
    crosstab_polls = [p for p in polls if p.get('has_crosstabs', False)]

    if not crosstab_polls:
        print("No polls with crosstabs available.")
        return None, None

    print(f"Found {len(crosstab_polls)} poll(s) with crosstabs:")
    for poll in crosstab_polls:
        print(f"  - {poll['name']}")

    # Get all unique demographic categories
    all_demographics = set()
    for poll in crosstab_polls:
        for cand in CANDIDATES:
            if cand in poll['crosstabs']:
                all_demographics.update(poll['crosstabs'][cand].keys())

    # Initialize aggregation
    weighted_crosstabs = {cand: {demo: 0.0 for demo in all_demographics} for cand in CANDIDATES}
    total_weights = {cand: {demo: 0.0 for demo in all_demographics} for cand in CANDIDATES}
    crosstab_moes = {demo: [] for demo in all_demographics}

    # Aggregate with weighting
    for poll in crosstab_polls:
        # Calculate poll weight (similar to main poll weighting)
        poll_weight, _ = calculate_poll_weight(poll)

        for cand in CANDIDATES:
            if cand not in poll['crosstabs']:
                continue

            for demo, pct in poll['crosstabs'][cand].items():
                # Get sample size for this demographic
                sample_size = poll.get('crosstab_sample_sizes', {}).get(demo, poll['sample_size'] * 0.2)

                # Weight by both poll quality and subsample size
                subsample_weight = np.sqrt(sample_size) / 10  # Normalize
                combined_weight = poll_weight * subsample_weight

                weighted_crosstabs[cand][demo] += pct * combined_weight
                total_weights[cand][demo] += combined_weight

                # Track MOE for this demographic
                moe = calculate_crosstab_moe(sample_size)
                crosstab_moes[demo].append(moe)

    # Calculate weighted averages
    averaged_crosstabs = {cand: {} for cand in CANDIDATES}
    for cand in CANDIDATES:
        for demo in all_demographics:
            if total_weights[cand][demo] > 0:
                averaged_crosstabs[cand][demo] = weighted_crosstabs[cand][demo] / total_weights[cand][demo]
            else:
                averaged_crosstabs[cand][demo] = 0

    # Calculate average MOE per demographic
    avg_demo_moes = {}
    for demo in all_demographics:
        if crosstab_moes[demo]:
            avg_demo_moes[demo] = np.mean(crosstab_moes[demo])
        else:
            avg_demo_moes[demo] = 10.0  # Default

    print("\nCrosstab Margins of Error by Demographic:")
    print(f"{'Demographic':<20s} {'Avg MOE':<10s} {'Reliability':<15s}")
    print("-" * 50)
    for demo, moe in sorted(avg_demo_moes.items(), key=lambda x: x[1]):
        reliability = "High" if moe < 8 else "Medium" if moe < 12 else "Low"
        print(f"{demo:<20s} ±{moe:>5.1f}%    {reliability:<15s}")

    return averaged_crosstabs, avg_demo_moes


def scale_crosstabs_to_polling_average(averaged_crosstabs, baseline_avg, crosstab_polls):
    """
    Scale crosstabs from their original poll averages to current polling average.

    Logic: If Fine was 10% when crosstabs were taken but is now 20% in polling average,
    scale all her demographic crosstabs proportionally.
    """
    if not averaged_crosstabs:
        return None

    print("\n" + "=" * 70)
    print("SCALING CROSSTABS TO CURRENT POLLING AVERAGE")
    print("=" * 70)

    # Calculate the average poll result at the time crosstabs were taken
    crosstab_baseline = {}
    total_weight = 0

    for poll in crosstab_polls:
        weight, _ = calculate_poll_weight(poll)
        for cand in CANDIDATES:
            crosstab_baseline[cand] = crosstab_baseline.get(cand, 0) + poll['results'].get(cand, 0) * weight
        total_weight += weight

    for cand in CANDIDATES:
        crosstab_baseline[cand] /= total_weight

    # Scale each candidate's crosstabs
    scaled_crosstabs = {cand: {} for cand in CANDIDATES}

    print(f"\n{'Candidate':<15s} {'Crosstab Base':<15s} {'Current Avg':<15s} {'Scaling Factor':<15s}")
    print("-" * 70)

    for cand in CANDIDATES:
        original_pct = crosstab_baseline.get(cand, 0)
        current_pct = baseline_avg.get(cand, 0)

        if original_pct > 0:
            scaling_factor = current_pct / original_pct
        else:
            scaling_factor = 1.0

        print(f"{cand:<15s} {original_pct:>7.1f}%        {current_pct:>7.1f}%        {scaling_factor:>7.2f}x")

        # Apply scaling with ceiling
        for demo, pct in averaged_crosstabs[cand].items():
            # Use diminishing returns for already-strong demographics
            if pct < 5:
                scaled_pct = pct * scaling_factor
            elif pct < 15:
                scaled_pct = pct * (scaling_factor ** 0.85)
            else:
                scaled_pct = pct * (scaling_factor ** 0.7)

            # Cap at 95% (can't have 100% of a demographic)
            scaled_crosstabs[cand][demo] = min(scaled_pct, 95.0)

    # Show examples
    print("\nExample Scaled Crosstabs (Fine):")
    print(f"{'Demographic':<20s} {'Original':<12s} {'Scaled':<12s}")
    print("-" * 50)
    for demo in list(averaged_crosstabs['Fine'].keys())[:5]:
        orig = averaged_crosstabs['Fine'][demo]
        scaled = scaled_crosstabs['Fine'][demo]
        print(f"{demo:<20s} {orig:>7.1f}%      {scaled:>7.1f}%")

    return scaled_crosstabs


def map_age_bucket(median_age, crosstabs):
    """
    Map precinct median age to crosstab age buckets with interpolation.
    Returns weighted support across adjacent buckets.
    """
    # Age bucket midpoints and ranges because crosstabs do not match my buckets
    buckets = [
        ('age_18-29', 18, 29, 23.5),
        ('age_30-44', 30, 44, 37),
        ('age_45-65', 45, 65, 55),
        ('age_65+', 65, 100, 72.5)
    ]

    # Find which bucket(s) this age falls into
    for i, (name, low, high, midpoint) in enumerate(buckets):
        if median_age <= high:
            if median_age < low and i > 0:
                # Interpolate between previous and current bucket
                prev_name, prev_low, prev_high, prev_mid = buckets[i-1]
                weight = (median_age - prev_mid) / (midpoint - prev_mid)
                weight = np.clip(weight, 0, 1)

                prev_val = crosstabs.get(prev_name, 0)
                curr_val = crosstabs.get(name, 0)
                return prev_val * (1 - weight) + curr_val * weight
            else:
                # Directly in this bucket
                return crosstabs.get(name, 0)

    # Default to oldest bucket
    return crosstabs.get('age_65+', 0)


def map_ideology_to_crosstab(prog_score, crosstabs):
    """
    Map prog_score to ideology crosstabs.
    prog_score: -1 (very moderate) to +1 (very progressive)
    """
    if prog_score > 0.5:
        return crosstabs.get('very_liberal', 0)
    elif prog_score > 0:
        # Interpolate between somewhat_liberal and very_liberal
        weight = prog_score / 0.5
        somewhat = crosstabs.get('somewhat_liberal', 0)
        very = crosstabs.get('very_liberal', 0)
        return somewhat * (1 - weight) + very * weight
    elif prog_score > -0.5:
        # Interpolate between moderate and somewhat_liberal
        weight = (prog_score + 0.5) / 0.5
        moderate = crosstabs.get('moderate', 0)
        somewhat = crosstabs.get('somewhat_liberal', 0)
        return moderate * (1 - weight) + somewhat * weight
    else:
        return crosstabs.get('moderate', 0)


# ============================================================================
# PRECINCT BIAS ENGINE (Enhanced with Crosstabs)
# ============================================================================

def calculate_district_wide_undecided_bias(scaled_crosstabs=None):
    """
    Loads precinct data and calculates district-wide undecided bias weights
    by aggregating precinct-level crosstab-based support estimates.

    For each precinct:
    - Determine demographic profile (ideology, age, race)
    - Look up support in crosstabs
    - Weight undecided allocation proportionally (with floor of 1 for 0% support)
    - Aggregate across district weighted by turnout
    """
    print(f"Loading precinct data from {PRECINCT_DATA_FILE}...")
    try:
        df = pd.read_csv(PRECINCT_DATA_FILE)
    except FileNotFoundError:
        print(f"WARNING: {PRECINCT_DATA_FILE} not found. Using neutral weights.")
        return {c: 1.0 for c in CANDIDATES}

    # Ensure required columns exist
    required_cols = ['prog_score_imputed', 'total_votes_projected', 'undecided_pct']
    for col in required_cols:
        if col not in df.columns:
            if col == 'undecided_pct':
                df[col] = 0.25
            elif col == 'prog_score_imputed':
                df[col] = 0
            elif col == 'total_votes_projected':
                df[col] = 500

    # Add demographic columns if missing
    if 'median_voting_age' not in df.columns:
        df['median_voting_age'] = 50
    if 'V_20_VAP_Black_pct' not in df.columns:
        df['V_20_VAP_Black_pct'] = 0.0
    if 'V_20_VAP_Asian_pct' not in df.columns:
        df['V_20_VAP_Asian_pct'] = 0.0

    # Define ideology thresholds (divide into thirds)
    prog_scores = df['prog_score_imputed'].dropna()
    if len(prog_scores) > 0:
        moderate_threshold = prog_scores.quantile(0.333)
        somewhat_lib_threshold = prog_scores.quantile(0.667)
    else:
        moderate_threshold = -0.3
        somewhat_lib_threshold = 0.3

    print(f"\nIdeology thresholds:")
    print(f"  Moderate: prog_score <= {moderate_threshold:.3f}")
    print(f"  Somewhat Liberal: {moderate_threshold:.3f} < prog_score <= {somewhat_lib_threshold:.3f}")
    print(f"  Very Liberal: prog_score > {somewhat_lib_threshold:.3f}")

    # Initialize weighted vote buckets
    weighted_counts = {c: 0.0 for c in CANDIDATES}
    total_undecided_mass = 0.0

    # --- USE CROSSTABS IF AVAILABLE ---
    if scaled_crosstabs:
        print("\nUsing crosstab-based undecided allocation...")

        for _, row in df.iterrows():
            # Estimate raw number of undecided voters in this precinct
            n_undecided = row.get('total_votes_projected', 500) * row.get('undecided_pct', 0.25)
            total_undecided_mass += n_undecided

            # Get precinct demographics
            prog_score = row.get('prog_score_imputed', 0)
            median_age = row.get('median_voting_age', 50)
            black_pct = row.get('V_20_VAP_Black_pct', 0)
            asian_pct = row.get('V_20_VAP_Asian_pct', 0)
            white_pct = max(0, 100 - black_pct - asian_pct)

            # Calculate support for each candidate in this precinct
            precinct_support = {}

            for cand in CANDIDATES:
                if cand not in scaled_crosstabs:
                    precinct_support[cand] = 1.0  # Floor
                    continue

                crosstabs = scaled_crosstabs[cand]
                support_components = []

                # 1. IDEOLOGY COMPONENT
                if prog_score <= moderate_threshold:
                    ideology_support = crosstabs.get('moderate', 0)
                elif prog_score <= somewhat_lib_threshold:
                    ideology_support = crosstabs.get('somewhat_liberal', 0)
                else:
                    ideology_support = crosstabs.get('very_liberal', 0)

                support_components.append(ideology_support)

                # 2. AGE COMPONENT
                age_support = map_age_to_crosstab(median_age, crosstabs)
                support_components.append(age_support)

                # 3. RACIAL/ETHNIC COMPONENT (composite based on precinct composition)
                white_support = crosstabs.get('white', 0)

                # Estimate Black support
                if 'black' in crosstabs:
                    black_support = crosstabs['black']
                else:
                    # Use heuristics for candidates without Black crosstabs
                    if cand == 'Simmons':
                        black_support = white_support * 3.0 if white_support > 0 else 15.0
                    elif cand in ['Abughazaleh', 'Huynh', 'Amiwala']:
                        black_support = white_support * 0.8 if white_support > 0 else 5.0
                    else:
                        black_support = white_support if white_support > 0 else 5.0

                # Estimate Asian support
                if 'asian' in crosstabs:
                    asian_support = crosstabs['asian']
                else:
                    if cand == 'Huynh':
                        asian_support = white_support * 2.5 if white_support > 0 else 15.0
                    elif cand == 'Amiwala':
                        asian_support = white_support * 2.0 if white_support > 0 else 12.0
                    else:
                        asian_support = white_support * 0.8 if white_support > 0 else 5.0

                # Composite racial support
                racial_support = (
                        (white_pct / 100) * white_support +
                        (black_pct / 100) * black_support +
                        (asian_pct / 100) * asian_support
                )
                support_components.append(racial_support)

                # Average across components
                avg_support = np.mean(support_components)

                # Apply floor of 1 for 0% support (everyone has a chance)
                precinct_support[cand] = max(avg_support, 1.0)

            # Add this precinct's weighted contribution
            for cand in CANDIDATES:
                weighted_counts[cand] += n_undecided * precinct_support[cand]

    else:
        # --- FALLBACK LOGIC (rule-based weights) ---
        print("\nNo crosstabs available, using rule-based weights...")

        for _, row in df.iterrows():
            n_undecided = row.get('total_votes_projected', 500) * row.get('undecided_pct', 0.25)
            total_undecided_mass += n_undecided

            region = str(row.get('region', 'Other')).lower()
            prog_score = row.get('prog_score_imputed', 0)

            # Start with neutral weight of 1.0 for everyone
            w = {c: 1.0 for c in CANDIDATES}

            # Ideology-based weights
            if prog_score <= moderate_threshold:
                w['Fine'] *= 1.4
                w['Andrew'] *= 1.3
                w['Biss'] *= 0.9
                w['Abughazaleh'] *= 0.7
                w['Simmons'] *= 0.7
            elif prog_score <= somewhat_lib_threshold:
                w['Biss'] *= 1.3
                w['Fine'] *= 1.0
                w['Abughazaleh'] *= 1.1
            else:
                w['Abughazaleh'] *= 1.4
                w['Simmons'] *= 1.3
                w['Amiwala'] *= 1.2
                w['Biss'] *= 1.1
                w['Fine'] *= 0.7

            # Regional adjustments
            if 'evanston' in region:
                w['Biss'] *= 0.6
            if 'niles' in region:
                w['Amiwala'] *= 1.4

            for cand in CANDIDATES:
                weighted_counts[cand] += n_undecided * w[cand]

    # Normalize into final weights relative to 1.0
    final_weights = {}
    if total_undecided_mass > 0:
        # Calculate average weight per candidate
        avg_weights = {cand: weighted_counts[cand] / total_undecided_mass for cand in CANDIDATES}

        # Normalize to mean of 1.0
        mean_weight = np.mean(list(avg_weights.values()))
        if mean_weight > 0:
            final_weights = {cand: avg_weights[cand] / mean_weight for cand in CANDIDATES}
        else:
            final_weights = {c: 1.0 for c in CANDIDATES}
    else:
        final_weights = {c: 1.0 for c in CANDIDATES}

    return final_weights


def map_age_to_crosstab(median_age, crosstabs):
    """
    Map precinct median age to crosstab age buckets with interpolation.
    Returns weighted support across adjacent buckets.
    """
    # Age bucket definitions (name, min, max, midpoint)
    buckets = [
        ('age_18-29', 18, 29, 23.5),
        ('age_30-44', 30, 44, 37),
        ('age_45-65', 45, 65, 55),
        ('age_65+', 65, 100, 72.5)
    ]

    # Handle edge cases
    if median_age < 30:
        return crosstabs.get('age_18-29', 0)
    if median_age >= 65:
        return crosstabs.get('age_65+', 0)

    # Find which buckets to interpolate between
    if 30 <= median_age < 45:
        lower = crosstabs.get('age_30-44', 0)
        upper = crosstabs.get('age_45-65', 0)
        weight = (median_age - 37) / (55 - 37)
    else:  # 45 <= median_age < 65
        lower = crosstabs.get('age_45-65', 0)
        upper = crosstabs.get('age_65+', 0)
        weight = (median_age - 55) / (72.5 - 55)

    weight = np.clip(weight, 0, 1)
    return lower * (1 - weight) + upper * weight


# ============================================================================
# CORE SIMULATION FUNCTIONS
# ============================================================================

def calculate_margin_of_error(sample_size):
    return (1 / np.sqrt(sample_size)) * 100


def apply_house_effect(poll):
    candidates = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh', 'Others']

    # If not an internal poll, no adjustment needed
    if not poll.get('is_internal', False):
        return poll['results'].copy(), poll.get('undecided', 0)

    internal_candidate = poll.get('internal_for')
    adjustment = poll.get('house_effect_adjustment', 0)

    # If no adjustment specified, return as-is
    if not internal_candidate or adjustment == 0:
        return poll['results'].copy(), poll.get('undecided', 0)

    adjusted_results = poll['results'].copy()
    current_undecided = poll.get('undecided', 0)

    # Take from the internal candidate and add to undecided
    if internal_candidate in adjusted_results:
        original_value = adjusted_results[internal_candidate]
        adjusted_results[internal_candidate] = max(0, original_value - adjustment)

        # Add the adjustment to undecided instead of other candidates
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
        return {cand: (trend_raw.get(cand, 0) / max_abs) * diversity_multiplier for cand in trend_raw}
    return {}


def calculate_poll_weight(poll):
    quality_weight = poll['pollster_quality']
    moe = poll.get('margin_of_error', calculate_margin_of_error(poll['sample_size']))
    moe_weight = 100 / moe
    poll_date = datetime.strptime(poll['date'], '%Y-%m-%d')
    days_old = (datetime.now() - poll_date).days
    recency_weight = 1.0 if days_old <= 7 else 0.5 ** ((days_old - 7) / 14)
    internal_penalty = 0.5 if poll.get('is_internal', False) else 1.0
    return quality_weight * moe_weight * recency_weight * internal_penalty, moe


def aggregate_polls(polls):
    candidates = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh', 'Others']
    poll_weights = []
    adjusted_polls = []
    adjusted_undecideds = []  # NEW: Track adjusted undecided values

    for poll in polls:
        adjusted_results, adjusted_undecided = apply_house_effect(poll)  # UPDATED: Now returns tuple
        adjusted_poll = poll.copy()
        adjusted_poll['results'] = adjusted_results
        adjusted_polls.append(adjusted_poll)
        adjusted_undecideds.append(adjusted_undecided)  # NEW: Store adjusted undecided
        weight, moe = calculate_poll_weight(poll)
        poll_weights.append(weight)

    total_weight = sum(poll_weights)
    weighted_results = {}

    for cand in candidates:
        weighted_sum = sum(poll['results'].get(cand, 0) * weight for poll, weight in zip(adjusted_polls, poll_weights))
        weighted_results[cand] = weighted_sum / total_weight

    total_named = sum(weighted_results[c] for c in candidates if c != 'Others')

    # Use adjusted undecided values instead of original
    undecided = sum(adj_und * weight for adj_und, weight in zip(adjusted_undecideds, poll_weights)) / total_weight

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
    """
    Allocates undecideds using the pre-calculated composite weights
    derived from precinct-level data.
    """
    candidates = [c for c in baseline.keys() if c != 'Others']
    allocation = {c: 0.0 for c in candidates}

    # Calculate the weighted share for each candidate
    weighted_shares = {}
    total_share = 0

    for cand in candidates:
        base_support = baseline.get(cand, 0)
        # Apply the geographic composite weight
        weight = composite_weights.get(cand, 1.0)

        # Undecideds follow baseline support biased by the weight
        share = base_support * weight
        weighted_shares[cand] = share
        total_share += share

    if total_share == 0:
        return allocation

    # Distribute the undecided bucket
    for cand in candidates:
        allocation[cand] = undecided_pct * (weighted_shares[cand] / total_share)

    return allocation


def simulate_election(baseline, undecided_pct, avg_moe, trend_signal, composite_weights):
    candidates = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']
    results = {}
    PRIMARY_VOLATILITY = 2.75 #primaries are much more volatile than general elections
    TREND_STRENGTH = 0.15 #might need to revisit because the only trend between the same pollster
    #is two Fine internals
    TREND_NOISE = 0.3

    # 1. Base Variability & Trend
    for cand in candidates:
        trend_effect = trend_signal.get(cand, 0) * TREND_STRENGTH * avg_moe
        trend_noise = np.random.normal(0, TREND_NOISE * avg_moe)
        error = np.random.normal(0, avg_moe * 0.5 * PRIMARY_VOLATILITY)
        results[cand] = max(0, baseline.get(cand, 0) + error + trend_effect + trend_noise)

    # 2. Breakout Events
    if np.random.rand() < 0.05:
        eligible = [c for c in candidates if results[c] < 15]
        if eligible:
            results[np.random.choice(eligible)] += np.random.uniform(3, 7)

    undecided_votes = undecided_pct

    # 3. Late Surge "Other" Breakout
    if np.random.rand() < 0.25:
        results['Other_Breakout'] = np.random.uniform(0.3, 0.7) * undecided_pct

    # 4. ALLOCATE UNDECIDEDS (The Hybrid/Smart Step)
    # We use the calculated composite_weights for the proportional share
    smart_allocation = allocate_smart_undecideds(
        undecided_votes * UNDECIDED_ALLOCATION['proportional'],
        baseline,
        composite_weights
    )

    for cand, votes in smart_allocation.items():
        if cand in results:
            results[cand] += votes

    # 5. Bandwagon Effect (Top candidates get extra undecideds)
    sorted_cands = sorted(results.items(), key=lambda x: x[1], reverse=True)
    top_3 = [c for c, v in sorted_cands[:3]]
    top_total = sum(results[c] for c in top_3)
    if top_total > 0:
        for cand in top_3:
            results[cand] += (results[cand] / top_total) * (undecided_votes * UNDECIDED_ALLOCATION['top_candidates'])

    # 6. Random Noise Allocation
    for cand in candidates:
        results[cand] += np.random.uniform(0, (undecided_votes * UNDECIDED_ALLOCATION['random']) / len(candidates) * 2)

    # Normalize to 100%
    total = sum(results.values())
    if total > 0:
        for cand in results:
            results[cand] = (results[cand] / total) * 100
    return results


def run_monte_carlo(polls, n_simulations=N_SIMULATIONS):
    print("=" * 70)
    print("MONTE CARLO WIN PROBABILITY SIMULATION")
    print("=" * 70)

    # Calculate baseline
    baseline, undecided_pct = aggregate_polls(polls)
    avg_moe = calculate_average_moe(polls)
    trend_signal = compute_trend_signal(polls)

    # --- PROCESS CROSSTABS ---
    crosstab_polls = [p for p in polls if p.get('has_crosstabs', False)]

    averaged_crosstabs = None
    scaled_crosstabs = None
    crosstab_moes = None

    if crosstab_polls:
        averaged_crosstabs, crosstab_moes = aggregate_crosstabs(polls)
        if averaged_crosstabs:
            scaled_crosstabs = scale_crosstabs_to_polling_average(
                averaged_crosstabs,
                baseline,
                crosstab_polls
            )
            # NEW: Print the scaled crosstabs
            print_crosstab_summary(scaled_crosstabs)

    # --- CALCULATE PRECINCT BIAS WEIGHTS ---
    print("\nCalculating precinct-level undecided biases...")
    composite_weights = calculate_district_wide_undecided_bias(scaled_crosstabs)
    print("Composite Undecided Weights Calculated:")
    for c, w in composite_weights.items():
        if w != 1.0:
            print(f"  {c:<15s}: {w:.2f}x multiplier")

    # --- PRINT WEIGHTED POLL AVERAGE ---
    print("\nBASELINE: WEIGHTED POLL AVERAGE")
    print("-" * 70)
    candidates = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']
    for cand in candidates:
        print(f"  {cand:15s}: {baseline.get(cand, 0):5.1f}%")
    print(f"\nUndecided: {undecided_pct:.1f}%")
    print(f"Average MOE: ±{avg_moe:.1f}%")
    print("-" * 70)

    tracking_candidates = candidates + ['Other_Breakout']
    wins = {cand: 0 for cand in tracking_candidates}
    all_results = {cand: [] for cand in tracking_candidates}
    best_scenarios = {cand: 0.0 for cand in candidates}  # Tracking high water mark

    print(f"\nRunning {n_simulations:,} simulations...")

    for i in range(n_simulations):
        if (i + 1) % 50000 == 0:
            print(f"  Completed {i + 1:,}/{n_simulations:,} simulations...")

        # Pass composite_weights to the simulation
        results = simulate_election(baseline, undecided_pct, avg_moe, trend_signal, composite_weights)
        winner = max(results.items(), key=lambda x: x[1])[0]

        if winner not in wins:
            wins[winner] = 0
            all_results[winner] = [0] * i

        wins[winner] += 1

        # Track ceilings (best outcome for each simulated run)
        for cand, score in results.items():
            if cand in best_scenarios:
                if score > best_scenarios[cand]:
                    best_scenarios[cand] = score

        for cand in tracking_candidates:
            all_results[cand].append(results.get(cand, 0))

    win_probs = {cand: (wins[cand] / n_simulations) * 100 for cand in candidates}
    percentiles = {cand: {p: np.percentile(all_results[cand], q) for p, q in
                          zip(['p10', 'p25', 'p50', 'p75', 'p90'], [10, 25, 50, 75, 90])} for cand in candidates}

    return win_probs, percentiles, all_results, wins, best_scenarios, scaled_crosstabs, crosstab_moes


def display_win_counts(wins, n_simulations):
    """Prints the raw number of wins each candidate achieved"""
    print("\n" + "=" * 70)
    print(f"RAW WIN COUNTS (Out of {n_simulations:,} Simulations)")
    print("=" * 70)

    sorted_wins = sorted(wins.items(), key=lambda x: x[1], reverse=True)
    print(f"{'Candidate':<20s} {'Wins':<15s}")
    print("-" * 40)
    for cand, count in sorted_wins:
        if count > 0:
            print(f"{cand:<20s} {count:<15,}")


def print_best_scenarios(best_scenarios):
    """Prints the highest percentage achieved by candidates"""
    print("\n" + "=" * 70)
    print("CEILING ANALYSIS: BEST POSSIBLE OUTCOMES")
    print("=" * 70)
    sorted_best = sorted(best_scenarios.items(), key=lambda x: x[1], reverse=True)
    for cand, high in sorted_best:
        print(f"  {cand:15s}: {high:5.1f}%")


def display_results(win_probs, percentiles):
    print("\n" + "=" * 70)
    print("WIN PROBABILITIES")
    print("=" * 70)
    sorted_probs = sorted(win_probs.items(), key=lambda x: x[1], reverse=True)
    print(f"\n{'Candidate':<15s} {'Win Prob':<12s} {'Likely Range (50%)':<25s}")
    print("-" * 70)
    for cand, prob in sorted_probs:
        p25, p75, p50 = percentiles[cand]['p25'], percentiles[cand]['p75'], percentiles[cand]['p50']
        bar = "█" * int(prob / 2)
        print(f"{cand:<15s} {prob:>5.1f}%  {bar:<25s} {p25:.1f}%-{p75:.1f}% (median: {p50:.1f}%)")


def create_visualization(win_probs, percentiles, all_results):
    candidates = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    sorted_probs = sorted(win_probs.items(), key=lambda x: x[1], reverse=True)
    cands, probs = zip(*sorted_probs)
    ax1.barh(cands, probs, color='skyblue')
    ax1.set_title('Win Probability (%)')
    ax2.boxplot([all_results[c] for c in cands if c in all_results], labels=[c for c in cands if c in all_results],
                vert=False)
    ax2.set_title('Distribution of Outcomes')
    plt.tight_layout()
    plt.savefig('win_probabilities.png')
    plt.close()


def print_crosstab_summary(scaled_crosstabs):
    """Print formatted summary of scaled crosstabs"""
    if not scaled_crosstabs:
        print("\nNo crosstabs available to display.")
        return

    print("\n" + "=" * 70)
    print("SCALED CROSSTABS - DEMOGRAPHIC SUPPORT PROFILES")
    print("=" * 70)

    # Get all demographics
    all_demographics = set()
    for cand_crosstabs in scaled_crosstabs.values():
        all_demographics.update(cand_crosstabs.keys())

    # Group demographics by type
    ideology_demos = sorted([d for d in all_demographics if 'liberal' in d or 'moderate' in d])
    age_demos = sorted([d for d in all_demographics if 'age' in d])
    gender_demos = sorted([d for d in all_demographics if d in ['male', 'female']])
    education_demos = sorted([d for d in all_demographics if 'college' in d])
    race_demos = sorted([d for d in all_demographics if d in ['white', 'black', 'asian', 'hispanic']])

    # Print ideology crosstabs
    if ideology_demos:
        print("\nIDEOLOGY:")
        print(f"{'Candidate':<15s} {'Moderate':<12s} {'Smwt Liberal':<15s} {'Very Liberal':<15s}")
        print("-" * 60)
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                mod = scaled_crosstabs[cand].get('moderate', 0)
                smwt = scaled_crosstabs[cand].get('somewhat_liberal', 0)
                very = scaled_crosstabs[cand].get('very_liberal', 0)
                print(f"{cand:<15s} {mod:>7.1f}%      {smwt:>7.1f}%         {very:>7.1f}%")

    # Print age crosstabs
    if age_demos:
        print("\nAGE:")
        header = f"{'Candidate':<15s}"
        for demo in age_demos:
            header += f" {demo:<12s}"
        print(header)
        print("-" * (15 + 13 * len(age_demos)))
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                row = f"{cand:<15s}"
                for demo in age_demos:
                    val = scaled_crosstabs[cand].get(demo, 0)
                    row += f" {val:>7.1f}%    "
                print(row)

    # Print gender crosstabs
    if gender_demos:
        print("\nGENDER:")
        print(f"{'Candidate':<15s} {'Female':<12s} {'Male':<12s}")
        print("-" * 45)
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                female = scaled_crosstabs[cand].get('female', 0)
                male = scaled_crosstabs[cand].get('male', 0)
                print(f"{cand:<15s} {female:>7.1f}%      {male:>7.1f}%")

    # Print education crosstabs
    if education_demos:
        print("\nEDUCATION:")
        print(f"{'Candidate':<15s} {'No College':<12s} {'College':<12s}")
        print("-" * 45)
        for cand in CANDIDATES:
            if cand in scaled_crosstabs:
                no_college = scaled_crosstabs[cand].get('no_college', 0)
                college = scaled_crosstabs[cand].get('college', 0)
                print(f"{cand:<15s} {no_college:>7.1f}%      {college:>7.1f}%")

    # Print race/ethnicity crosstabs
    if race_demos:
        print("\nRACE/ETHNICITY:")
        header = f"{'Candidate':<15s}"
        for demo in race_demos:
            header += f" {demo.capitalize():<12s}"
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
if __name__ == "__main__":
    if len(POLLS) == 0:
        print("\nERROR: No polls configured!")
        exit(1)

    # Modified call to include crosstabs
    win_probs, percentiles, all_results, wins, best_scenarios, scaled_crosstabs, crosstab_moes = run_monte_carlo(POLLS, N_SIMULATIONS)

    # Print outputs
    display_win_counts(wins, N_SIMULATIONS)
    display_results(win_probs, percentiles)
    print_best_scenarios(best_scenarios)
    print_crosstab_summary(scaled_crosstabs)

    create_visualization(win_probs, percentiles, all_results)

    # Export forecast for precinct-level model
    baseline, undecided_pct = aggregate_polls(POLLS)
    avg_moe = calculate_average_moe(POLLS)

    CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']
    median_forecast = {cand: np.percentile(all_results[cand], 50) for cand in CANDIDATES}

    # Export both forecasts and win probabilities
    with open('poll_baseline.json', 'w') as f:
        json.dump({
            'baseline': baseline,
            'median_forecast': median_forecast,
            'undecided_pct': undecided_pct,
            'avg_moe': avg_moe,
            'scaled_crosstabs': scaled_crosstabs,  # NEW: Export scaled crosstabs
            'crosstab_moes': crosstab_moes  # NEW: Export crosstab margins of error
        }, f, indent=2)

    with open('district_win_probabilities.json', 'w') as f:
        json.dump({
            'win_probabilities': win_probs,
            'median_results': median_forecast,
            'simulation_wins': wins
        }, f, indent=2)

    print("\n✓ Forecast exported to poll_baseline.json (including scaled crosstabs)")
    print("✓ District win probabilities exported to district_win_probabilities.json")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE!")
    print("=" * 70)