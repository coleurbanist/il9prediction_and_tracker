import pandas as pd
import numpy as np
import json
from typing import Dict

# ============================================================================
# CONFIGURATION
# ============================================================================

from poll_config import UNDECIDED_ALLOCATION, CANDIDATES

# Simulation Settings
N_SIMULATIONS = 50000
MOE_DISTRICT = 4.4
MOE_PRECINCT = 6.0

# Biss incumbency penalty in Evanston
BISS_EVANSTON_UNDECIDED_PENALTY = 0.65  # Undecideds 35% less likely to break for him

INPUT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
OUTPUT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
POLL_BASELINE_FILE = 'poll_baseline.json'
DISTRICT_RESULTS_FILE = 'district_win_probabilities.json'


# ============================================================================
# LOAD DATA
# ============================================================================

# Add this import at the top with the other imports
from datetime import datetime
import shutil


# ============================================================================
# LOAD DATA
# ============================================================================

def load_data():
    """Load all necessary data files"""
    print("Loading data...")

    df = pd.read_csv(INPUT_CSV)

    # CREATE BACKUP WITH TIMESTAMP
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    backup_path = INPUT_CSV.replace('.csv', f'_old_{timestamp}.csv')
    shutil.copy2(INPUT_CSV, backup_path)
    print(f"✓ Created backup: {backup_path}")

    with open(POLL_BASELINE_FILE, 'r') as f:
        poll_data = json.load(f)
        baseline_avg = poll_data['baseline']
        avg_moe = poll_data['avg_moe']
        scaled_crosstabs = poll_data.get('scaled_crosstabs')
        crosstab_moes = poll_data.get('crosstab_moes')

    with open(DISTRICT_RESULTS_FILE, 'r') as f:
        district_data = json.load(f)
        target_median = district_data['median_results']

    print(f"✓ Loaded {len(df)} precincts")
    if scaled_crosstabs:
        print(f"✓ Loaded scaled crosstabs for demographic modeling")
    else:
        print(f"⚠ No crosstabs available, will use fallback geographic boosts")

    return df, baseline_avg, target_median, avg_moe, scaled_crosstabs, crosstab_moes

# ============================================================================
# CROSSTAB HELPER FUNCTIONS
# ============================================================================

def map_age_to_crosstab(median_age, crosstabs):
    """
    Map precinct median age to crosstab age buckets with interpolation.
    """
    # Age bucket definitions (name, min, max, midpoint)
    buckets = [
        ('age_18-29', 18, 29, 23.5),
        ('age_30-44', 30, 44, 37),
        ('age_45-65', 45, 65, 55),
        ('age_65+', 65, 100, 72.5)
    ]


    if median_age < 30:
        return crosstabs.get('age_18-29', 0)
    if median_age >= 65:
        return crosstabs.get('age_65+', 0)


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
# STEP 1: APPLY CROSSTAB-BASED DEMOGRAPHIC MODELING
# ============================================================================
# In the apply_crosstab_modeling function, update the Biss Evanston boost:
def apply_crosstab_modeling(df, baseline_avg, scaled_crosstabs):
    """
    Apply crosstab-based demographic modeling to estimate precinct-level support.
    Uses ideology, age, and racial composition from crosstabs.
    """
    print("\nApplying crosstab-based demographic modeling...")

    # Define ideology thresholds (divide into thirds)
    prog_scores = df['prog_score_imputed'].dropna()
    if len(prog_scores) > 0:
        moderate_threshold = prog_scores.quantile(0.333)
        somewhat_lib_threshold = prog_scores.quantile(0.667)
    else:
        moderate_threshold = -0.3
        somewhat_lib_threshold = 0.3

    print(f"Ideology thresholds:")
    print(f"  Moderate: <= {moderate_threshold:.3f}")
    print(f"  Somewhat Liberal: {moderate_threshold:.3f} to {somewhat_lib_threshold:.3f}")
    print(f"  Very Liberal: > {somewhat_lib_threshold:.3f}")

    # Ensure demographic columns exist
    if 'median_voting_age' not in df.columns:
        df['median_voting_age'] = 50
    if 'V_20_VAP_Black_pct' not in df.columns:
        df['V_20_VAP_Black_pct'] = 0.0
    if 'V_20_VAP_Asian_pct' not in df.columns:
        df['V_20_VAP_Asian_pct'] = 0.0

    # Calculate support for each candidate in each precinct
    for cand in CANDIDATES:
        if scaled_crosstabs and cand in scaled_crosstabs:
            crosstabs = scaled_crosstabs[cand]
            district_avg = baseline_avg.get(cand, 0)

            precinct_support = []

            for idx, row in df.iterrows():
                support_components = []

                # 1. IDEOLOGY COMPONENT
                prog_score = row.get('prog_score_imputed', 0)
                if prog_score <= moderate_threshold:
                    ideology_support = crosstabs.get('moderate', district_avg)
                elif prog_score <= somewhat_lib_threshold:
                    ideology_support = crosstabs.get('somewhat_liberal', district_avg)
                else:
                    ideology_support = crosstabs.get('very_liberal', district_avg)

                support_components.append(ideology_support)

                # 2. AGE COMPONENT
                median_age = row.get('median_voting_age', 50)
                age_support = map_age_to_crosstab(median_age, crosstabs)
                if age_support > 0:
                    support_components.append(age_support)

                # 3. RACIAL/ETHNIC COMPONENT
                black_pct = row.get('V_20_VAP_Black_pct', 0)
                asian_pct = row.get('V_20_VAP_Asian_pct', 0)
                white_pct = max(0, 100 - black_pct - asian_pct)

                white_support = crosstabs.get('white', district_avg)

                # Estimate Black support
                if 'black' in crosstabs:
                    black_support = crosstabs['black']
                else:
                    # Heuristics for candidates without Black crosstabs
                    if cand == 'Simmons':
                        black_support = white_support * 3.0 if white_support > 0 else district_avg * 3.0

                    else:
                        black_support = white_support if white_support > 0 else district_avg

                # Estimate Asian support
                if 'asian' in crosstabs:
                    asian_support = crosstabs['asian']
                else:
                    if cand == 'Huynh':
                        asian_support = white_support * 2.5 if white_support > 0 else district_avg * 2.5
                    else:
                        asian_support = white_support * 0.8 if white_support > 0 else district_avg * 0.8

                # Composite racial support
                racial_support = (
                        (white_pct / 100) * white_support +
                        (black_pct / 100) * black_support +
                        (asian_pct / 100) * asian_support
                )
                support_components.append(racial_support)

                # Average across components
                avg_support = np.mean(support_components)
                precinct_support.append(avg_support)

            df[f'raw_{cand}'] = precinct_support

        else:
            # Fallback to baseline if no crosstabs
            df[f'raw_{cand}'] = baseline_avg.get(cand, 0)

    # ========================================================================
    # HOMETOWN/LOCAL BOOSTS FOR DECIDED VOTERS
    # ========================================================================

    # Special boost for Biss in Evanston (hometown incumbent advantage)
    evanston_mask = df['in_evanston'] == 1
    if evanston_mask.sum() > 0:
        current_biss_evanston = df.loc[evanston_mask, 'raw_Biss'].mean()
        target_biss_evanston = 42.5  # Target 40-45% range

        if current_biss_evanston > 0:
            biss_evanston_multiplier = target_biss_evanston / current_biss_evanston
        else:
            biss_evanston_multiplier = 2.5

        # Cap the multiplier at something reasonable
        biss_evanston_multiplier = min(biss_evanston_multiplier, 3.5)
        #this is so high because I think he will get about 40% in Evanston and this gets the numbers close
        #this could be one of my boldest and most incorrect assumptions.

        print(f"\nApplying Evanston hometown boost for Biss:")
        print(f"  {evanston_mask.sum()} Evanston precincts")
        print(f"  Current avg support: {current_biss_evanston:.1f}%")
        print(f"  Target support: {target_biss_evanston:.1f}%")
        print(f"  Multiplier: {biss_evanston_multiplier:.2f}x")

        df.loc[evanston_mask, 'raw_Biss'] *= biss_evanston_multiplier

        new_biss_evanston = df.loc[evanston_mask, 'raw_Biss'].mean()
        print(f"  New avg support: {new_biss_evanston:.1f}%")

    # Special boost for Abughazaleh in Chicago because I suspect she will do better in Chicago
    # She gets local recognition boost, but smaller than Biss
    chicago_mask = df['in_chicago'] == 1
    if chicago_mask.sum() > 0:
        current_kat_chicago = df.loc[chicago_mask, 'raw_Abughazaleh'].mean()

        # i suspect this boost will be less for kat than Biss has in Evanston

        kat_chicago_multiplier = 1.175

        print(f"\nApplying Chicago local boost for Abughazaleh:")
        print(f"  {chicago_mask.sum()} Chicago precincts")
        print(f"  Current avg support: {current_kat_chicago:.1f}%")
        print(f"  Multiplier: {kat_chicago_multiplier:.2f}x")

        df.loc[chicago_mask, 'raw_Abughazaleh'] *= kat_chicago_multiplier

        new_kat_chicago = df.loc[chicago_mask, 'raw_Abughazaleh'].mean()
        print(f"  New avg support: {new_kat_chicago:.1f}%")
        print(f"  Absolute boost: +{new_kat_chicago - current_kat_chicago:.1f} percentage points")

        # 3. SIMMONS & HUYNH: Chicago local boosts
        if chicago_mask.sum() > 0:
            for cand in ['Simmons', 'Huynh']:
                current_support = df.loc[chicago_mask, f'raw_{cand}'].mean()
                # Apply same local multiplier as Abughazaleh
                multiplier = 1.5

                print(f"\nApplying Chicago local boost for {cand}:")
                print(f"  Multiplier: {multiplier:.2f}x")

                df.loc[chicago_mask, f'raw_{cand}'] *= multiplier

                new_support = df.loc[chicago_mask, f'raw_{cand}'].mean()
                print(f"  New avg support: {new_support:.1f}% (+{new_support - current_support:.1f})")

        # 4. AMIWALA: Niles Township Progressive Boost since she is from there
        township_col = next((col for col in ['Township', 'township', 'Township_Name'] if col in df.columns), None)

        if township_col:
            # Filter: Inside Niles Township AND Ideology score > somewhat_liberal threshold
            niles_mask = df[township_col].astype(str).str.contains('Niles', case=False, na=False)
            prog_niles_mask = niles_mask & (df['prog_score_imputed'] > somewhat_lib_threshold)

            if prog_niles_mask.sum() > 0:
                current_amiwala = df.loc[prog_niles_mask, 'raw_Amiwala'].mean()
                # Stronger boost to "pin" these precincts for her
                amiwala_multiplier = 1.5

                print(f"\nApplying Progressive/Niles boost for Amiwala:")
                print(f"  {prog_niles_mask.sum()} target precincts")
                print(f"  Current avg support: {current_amiwala:.1f}%")
                print(f"  Multiplier: {amiwala_multiplier:.2f}x")

                df.loc[prog_niles_mask, 'raw_Amiwala'] *= amiwala_multiplier

                new_amiwala = df.loc[prog_niles_mask, 'raw_Amiwala'].mean()
                print(f"  New avg support: {new_amiwala:.1f}%")
                # In the apply_crosstab_modeling function, after the Abughazaleh Chicago boost section, add:

                # 5. FINE: Chicago penalty (performs worse in the city)
                chicago_mask = df['in_chicago'] == 1
                if chicago_mask.sum() > 0:
                    current_fine_chicago = df.loc[chicago_mask, 'raw_Fine'].mean()

                    # Apply penalty - the inverse of what we gave Kat
                    # Fine does worse in Chicago than her crosstab model predicts
                    fine_chicago_penalty = 0.85  # 15% penalty (inverse of Kat's 1.175x boost)

                    print(f"\nApplying Chicago penalty for Fine:")
                    print(f"  {chicago_mask.sum()} Chicago precincts")
                    print(f"  Current avg support: {current_fine_chicago:.1f}%")
                    print(f"  Penalty multiplier: {fine_chicago_penalty:.2f}x")

                    df.loc[chicago_mask, 'raw_Fine'] *= fine_chicago_penalty

                    new_fine_chicago = df.loc[chicago_mask, 'raw_Fine'].mean()
                    print(f"  New avg support: {new_fine_chicago:.1f}%")
                    print(f"  Absolute change: {new_fine_chicago - current_fine_chicago:.1f} percentage points")
        else:
            print("\n⚠ Could not apply Amiwala boost: 'Township' column not found in data.")

    return df

# ============================================================================
# STEP 2: CALIBRATE TO DISTRICT BASELINE
# ============================================================================

def calibrate_to_baseline(df, baseline_avg, max_iterations=50, tolerance=0.5):
    """
    Calibrate precinct estimates to match district-wide baseline within 0.5 points.
    Uses additive adjustments to preserve geographic variation.
    """
    print("\nCalibrating to district baseline...")

    total_turnout = df['estimated_turnout'].sum()

    # Copy raw to adjusted
    for cand in CANDIDATES:
        df[f'adjusted_{cand}'] = df[f'raw_{cand}']

    for iteration in range(max_iterations):
        # Calculate current district-wide averages
        current_avg = {}
        for cand in CANDIDATES:
            weighted_sum = (df[f'adjusted_{cand}'] * df['estimated_turnout']).sum()
            current_avg[cand] = weighted_sum / total_turnout

        # Check convergence
        max_diff = max(abs(current_avg[cand] - baseline_avg.get(cand, 0)) for cand in CANDIDATES)

        if max_diff < tolerance:
            print(f"  ✓ Converged after {iteration + 1} iterations (max diff: {max_diff:.3f}%)")
            break

        # Apply ADDITIVE correction (preserves geographic variation)
        for cand in CANDIDATES:
            diff = baseline_avg.get(cand, 0) - current_avg[cand]
            df[f'adjusted_{cand}'] += diff
            df[f'adjusted_{cand}'] = np.maximum(df[f'adjusted_{cand}'], 0.1)

    else:
        print(f"  ⚠ Did not fully converge after {max_iterations} iterations")

    # Print results
    print("\nBaseline Calibration Results:")
    print(f"{'Candidate':<15s} {'Target':<10s} {'Achieved':<10s} {'Diff':<10s}")
    print("-" * 50)
    for cand in CANDIDATES:
        weighted_sum = (df[f'adjusted_{cand}'] * df['estimated_turnout']).sum()
        achieved = weighted_sum / total_turnout
        diff = achieved - baseline_avg.get(cand, 0)
        print(f"{cand:<15s} {baseline_avg.get(cand, 0):>9.2f}% {achieved:>9.2f}% {diff:>9.2f}%")

    return df


# ============================================================================
# STEP 3: CROSSTAB-BASED UNDECIDED ALLOCATION
# ============================================================================

def allocate_undecideds_crosstab_based(df, scaled_crosstabs, baseline_avg):
    """
    Allocate undecided voters using crosstab-based weights.
    Applies Biss penalty in Evanston and compensates elsewhere.
    Mainly because I think undecided voters in Evanston already know Biss and
    there is a reason they are undecided
    """
    print("\nAllocating undecided voters using crosstab-based modeling...")

    # Define ideology thresholds
    prog_scores = df['prog_score_imputed'].dropna()
    if len(prog_scores) > 0:
        moderate_threshold = prog_scores.quantile(0.333)
        somewhat_lib_threshold = prog_scores.quantile(0.667)
    else:
        moderate_threshold = -0.3
        somewhat_lib_threshold = 0.3

    # Calculate total undecided mass and Evanston share
    total_undecided_mass = 0
    evanston_undecided_mass = 0

    for idx, row in df.iterrows():
        decided_pct = sum(row[f'adjusted_{cand}'] for cand in CANDIDATES)
        undecided_pct = max(0, 100 - decided_pct)
        n_undecided = row['estimated_turnout'] * (undecided_pct / 100)

        total_undecided_mass += n_undecided
        if row.get('in_evanston', 0) == 1:
            evanston_undecided_mass += n_undecided

    print(f"  Total undecided voters: {total_undecided_mass:.0f}")
    print(f"  Evanston undecided voters: {evanston_undecided_mass:.0f} ({evanston_undecided_mass/total_undecided_mass*100:.1f}%)")

    # Calculate Biss compensation factor for non-Evanston precincts
    # Biss loses votes in Evanston, gains them elsewhere proportionally so that it balances overall
    biss_evanston_penalty_effect = evanston_undecided_mass * (1 - BISS_EVANSTON_UNDECIDED_PENALTY)
    non_evanston_undecided_mass = total_undecided_mass - evanston_undecided_mass

    if non_evanston_undecided_mass > 0:
        biss_non_evanston_boost = 1 + (biss_evanston_penalty_effect / non_evanston_undecided_mass)
    else:
        biss_non_evanston_boost = 1.0

    print(f"  Biss non-Evanston undecided boost: {biss_non_evanston_boost:.3f}x")

    # Allocate undecideds precinct by precinct
    for idx, row in df.iterrows():
        decided_pct = sum(row[f'adjusted_{cand}'] for cand in CANDIDATES)
        undecided_pct = max(0, 100 - decided_pct)

        if undecided_pct == 0:
            # No undecideds, just copy adjusted to final
            for cand in CANDIDATES:
                df.loc[idx, f'final_{cand}'] = row[f'adjusted_{cand}']
            continue

        # Get precinct demographics
        prog_score = row.get('prog_score_imputed', 0)
        median_age = row.get('median_voting_age', 50)
        black_pct = row.get('V_20_VAP_Black_pct', 0)
        asian_pct = row.get('V_20_VAP_Asian_pct', 0)
        white_pct = max(0, 100 - black_pct - asian_pct)
        is_evanston = row.get('in_evanston', 0) == 1

        # Calculate undecided support for each candidate
        precinct_undecided_support = {}

        if scaled_crosstabs:
            for cand in CANDIDATES:
                if cand not in scaled_crosstabs:
                    precinct_undecided_support[cand] = 1.0  # Floor
                    continue

                crosstabs = scaled_crosstabs[cand]
                support_components = []

                # 1. Ideology
                if prog_score <= moderate_threshold:
                    ideology_support = crosstabs.get('moderate', 0)
                elif prog_score <= somewhat_lib_threshold:
                    ideology_support = crosstabs.get('somewhat_liberal', 0)
                else:
                    ideology_support = crosstabs.get('very_liberal', 0)

                support_components.append(ideology_support)

                # 2. Age
                age_support = map_age_to_crosstab(median_age, crosstabs)
                support_components.append(age_support)

                # 3. Race/ethnicity
                white_support = crosstabs.get('white', 0)

                if 'black' in crosstabs:
                    black_support = crosstabs['black']
                else:
                    if cand == 'Simmons':
                        black_support = white_support * 3.0 if white_support > 0 else 15.0

                    else:
                        black_support = white_support if white_support > 0 else 5.0

                if 'asian' in crosstabs:
                    asian_support = crosstabs['asian']
                else:
                    if cand == 'Huynh':
                        asian_support = white_support * 2.5 if white_support > 0 else 15.0
                    elif cand == 'Amiwala':
                        asian_support = white_support * 2.0 if white_support > 0 else 12.0
                    else:
                        asian_support = white_support * 0.8 if white_support > 0 else 5.0

                racial_support = (
                    (white_pct / 100) * white_support +
                    (black_pct / 100) * black_support +
                    (asian_pct / 100) * asian_support
                )
                support_components.append(racial_support)

                # Average
                avg_support = np.mean(support_components)

                # Apply floor
                precinct_undecided_support[cand] = max(avg_support, 1.0)

                # Apply Biss modifiers
                if cand == 'Biss':
                    if is_evanston:
                        # Penalty in Evanston
                        precinct_undecided_support[cand] *= BISS_EVANSTON_UNDECIDED_PENALTY
                    else:
                        # Boost elsewhere
                        precinct_undecided_support[cand] *= biss_non_evanston_boost

        else:
            # Fallback: use current support as proxy
            for cand in CANDIDATES:
                precinct_undecided_support[cand] = max(row[f'adjusted_{cand}'], 1.0)

                if cand == 'Biss':
                    if is_evanston:
                        precinct_undecided_support[cand] *= BISS_EVANSTON_UNDECIDED_PENALTY
                    else:
                        precinct_undecided_support[cand] *= biss_non_evanston_boost

        # Normalize to sum to 1
        total_support = sum(precinct_undecided_support.values())
        if total_support > 0:
            for cand in CANDIDATES:
                precinct_undecided_support[cand] /= total_support
        else:
            # Equal split if all zero
            for cand in CANDIDATES:
                precinct_undecided_support[cand] = 1.0 / len(CANDIDATES)

        # Allocate undecideds
        for cand in CANDIDATES:
            df.loc[idx, f'final_{cand}'] = (
                row[f'adjusted_{cand}'] +
                undecided_pct * precinct_undecided_support[cand]
            )

    return df


# ============================================================================
# STEP 4: FINAL CALIBRATION TO TARGET MEDIAN
# ============================================================================

def final_calibrate(df, target_median, max_iterations=50, tolerance=0.5):
    """
    Calibrate to match district-wide median projection within 0.5 points.
    """
    print("\nFinal calibration to target median projection...")

    total_turnout = df['estimated_turnout'].sum()

    for iteration in range(max_iterations):
        current_avg = {}
        for cand in CANDIDATES:
            weighted_sum = (df[f'final_{cand}'] * df['estimated_turnout']).sum()
            current_avg[cand] = weighted_sum / total_turnout

        max_diff = max(abs(current_avg[cand] - target_median.get(cand, 0)) for cand in CANDIDATES)

        if max_diff < tolerance:
            print(f"  ✓ Converged after {iteration + 1} iterations (max diff: {max_diff:.3f}%)")
            break

        # Gentle additive correction
        for cand in CANDIDATES:
            diff = target_median.get(cand, 0) - current_avg[cand]
            df[f'final_{cand}'] += diff * 0.3
            df[f'final_{cand}'] = np.maximum(df[f'final_{cand}'], 0.1)

    # Print results
    print("\nFinal Calibration:")
    print(f"{'Candidate':<15s} {'Target':<10s} {'Achieved':<10s} {'Diff':<10s}")
    print("-" * 50)
    for cand in CANDIDATES:
        weighted_sum = (df[f'final_{cand}'] * df['estimated_turnout']).sum()
        achieved = weighted_sum / total_turnout
        diff = achieved - target_median.get(cand, 0)
        print(f"{cand:<15s} {target_median.get(cand, 0):>9.2f}% {achieved:>9.2f}% {diff:>9.2f}%")

    return df


# ============================================================================
# STEP 5: MONTE CARLO SIMULATIONS
# ============================================================================

def run_precinct_monte_carlo(df, avg_moe):
    print(f"\nRunning {N_SIMULATIONS:,} Monte Carlo simulations...")

    n_precincts = len(df)
    n_candidates = len(CANDIDATES)

    baselines = np.zeros((n_precincts, n_candidates))
    for i, cand in enumerate(CANDIDATES):
        baselines[:, i] = df[f'final_{cand}'].values

    baselines = baselines / 100

    # Correlated errors
    MODERATES = ['Fine', 'Andrew']
    BISS = ['Biss']
    OTHER_PROGRESSIVES = ['Abughazaleh', 'Simmons', 'Amiwala', 'Huynh']

    ideological_errors = np.random.normal(0, MOE_DISTRICT * 0.01 * 0.7, size=(N_SIMULATIONS, 3))
    individual_noise = np.random.normal(0, MOE_DISTRICT * 0.01 * 0.3, size=(N_SIMULATIONS, n_candidates))

    district_noise = np.zeros((N_SIMULATIONS, n_candidates))
    for i, cand in enumerate(CANDIDATES):
        if cand in MODERATES:
            district_noise[:, i] = ideological_errors[:, 0] + individual_noise[:, i]
        elif cand in BISS:
            district_noise[:, i] = ideological_errors[:, 1] + individual_noise[:, i]
        elif cand in OTHER_PROGRESSIVES:
            district_noise[:, i] = ideological_errors[:, 2] + individual_noise[:, i]

    local_noise = np.random.normal(0, MOE_PRECINCT * 0.01, size=(N_SIMULATIONS, n_precincts, n_candidates))

    base_3d = baselines[np.newaxis, :, :]
    noise_3d = district_noise[:, np.newaxis, :]

    simulated_pcts = base_3d + noise_3d + local_noise
    simulated_pcts = np.maximum(simulated_pcts, 0)

    sums = simulated_pcts.sum(axis=2, keepdims=True)
    simulated_pcts = simulated_pcts / sums

    winners_idx = np.argmax(simulated_pcts, axis=2)

    results = {}
    results = {}
    turnout = df['estimated_turnout'].values  # Get turnout array

    for i, cand in enumerate(CANDIDATES):
        wins = (winners_idx == i).sum(axis=0)
        win_prob = wins / N_SIMULATIONS
        median_pct = np.median(simulated_pcts[:, :, i], axis=0) * 100

        # Calculate median votes (rounded to nearest whole number)
        median_votes = np.round(median_pct / 100 * turnout).astype(int)

        results[f'win_prob_{cand}'] = win_prob
        results[f'median_pct_{cand}'] = median_pct
        results[f'median_votes_{cand}'] = median_votes  # ADD THIS LINE

    for col_name, data in results.items():
        df[col_name] = data

    print("✓ Simulations complete")

    return df


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("PRECINCT-LEVEL MONTE CARLO SIMULATOR V3")
    print("With Crosstab-Based Demographic Modeling")
    print("=" * 70)

    # Load data (this now includes backup creation)
    df, baseline_avg, target_median, avg_moe, scaled_crosstabs, crosstab_moes = load_data()

    # Step 1: Apply crosstab-based modeling
    df = apply_crosstab_modeling(df, baseline_avg, scaled_crosstabs)

    # Step 2: Calibrate to baseline
    df = calibrate_to_baseline(df, baseline_avg)

    # Step 3: Allocate undecideds with crosstab-based weights
    df = allocate_undecideds_crosstab_based(df, scaled_crosstabs, baseline_avg)

    # Step 4: Final calibration to target median
    df = final_calibrate(df, target_median)

    # Step 5: Monte Carlo simulations
    df = run_precinct_monte_carlo(df, avg_moe)

    # Save full results to original CSV
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✓ Full results saved to {OUTPUT_CSV}")

    # CREATE SIMPLIFIED OUTPUT CSV
    # Columns to keep: JoinField, JoinField2, estimated_turnout, + all simulation results
    simplified_columns = ['JoinField', 'JoinFieldAlt', 'estimated_turnout']

    # Add all candidate-related columns
    for cand in CANDIDATES:
        simplified_columns.extend([
            f'win_prob_{cand}',
            f'median_pct_{cand}',
            f'median_votes_{cand}'
        ])

    # Filter to only columns that exist in the dataframe
    available_columns = [col for col in simplified_columns if col in df.columns]
    df_simplified = df[available_columns].copy()
    # Convert median_pct columns to decimal form (divide by 100)
    for cand in CANDIDATES:
        pct_col = f'median_pct_{cand}'
        if pct_col in df_simplified.columns:
            df_simplified[pct_col] = df_simplified[pct_col] / 100

    # Create simplified CSV with timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    simplified_path = OUTPUT_CSV.replace('.csv', f'_simplified.csv')
    df_simplified.to_csv(simplified_path, index=False)
    print(f"✓ Simplified results saved to {simplified_path}")

    # Show geographic variation in results
    print("\n" + "=" * 70)
    print("GEOGRAPHIC VARIATION CHECK")
    print("=" * 70)

    evanston = df[df['in_evanston'] == 1]
    if len(evanston) > 0:
        print(f"\nEvanston (n={len(evanston)}):")
        print(f"  Biss median: {evanston['median_pct_Biss'].median():.1f}%")
        print(f"  Fine median: {evanston['median_pct_Fine'].median():.1f}%")
        print(f"  Abughazaleh median: {evanston['median_pct_Abughazaleh'].median():.1f}%")

    chicago = df[df['in_chicago'] == 1]
    if len(chicago) > 0:
        print(f"\nChicago (n={len(chicago)}):")
        print(f"  Simmons median: {chicago['median_pct_Simmons'].median():.1f}%")
        print(f"  Abughazaleh median: {chicago['median_pct_Abughazaleh'].median():.1f}%")
        print(f"  Fine median: {chicago['median_pct_Fine'].median():.1f}%")
        print(f"  Biss median: {chicago['median_pct_Biss'].median():.1f}%")

    suburbs = df[df['in_chicago'] == 0]
    if len(suburbs) > 0:
        print(f"\nSuburbs excluding Evanston (n={len(suburbs) - len(evanston)}):")
        suburbs_no_ev = suburbs[suburbs['in_evanston'] == 0]
        if len(suburbs_no_ev) > 0:
            print(f"  Fine median: {suburbs_no_ev['median_pct_Fine'].median():.1f}%")
            print(f"  Biss median: {suburbs_no_ev['median_pct_Biss'].median():.1f}%")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE!")
    print("=" * 70)
    print(f"\nFiles created:")
    print(f"  - Full dataset: {OUTPUT_CSV}")
    print(f"  - Simplified results: {simplified_path}")


if __name__ == "__main__":
    main()