import pandas as pd
import numpy as np
import json
from typing import Dict
import geopandas as gpd
from datetime import datetime
import shutil

# ============================================================================
# CONFIGURATION
# ============================================================================

from poll_config import UNDECIDED_ALLOCATION, CANDIDATES

# Simulation Settings
N_SIMULATIONS = 50000
MOE_DISTRICT = 4.4
MOE_PRECINCT = 6.0

# Biss incumbency penalty in Evanston (undecideds only — decided voters handled
# via senate district crosstabs which already show his Evanston strength)
BISS_EVANSTON_UNDECIDED_PENALTY = 0.65  # Undecideds 35% less likely to break for him

# Senate district numbers asked about in the PPP poll.
# Precincts get their support estimates from whichever district they overlap.
# If a precinct overlaps multiple districts, support is a weighted average
# based on area overlap. Precincts outside all three use sd_other data.
PPP_SENATE_DISTRICTS = [7, 8, 9]   # SD-7 (Evanston/North Shore), SD-8 (North Chicago), SD-9 (NW Chicago suburbs)

# File paths
SHAPEFILE_PATH = 'data/shapefile/IL24/IL24.shp'
CONGRESSIONAL_DISTRICTS_PATH = 'data/shapefile/congressional_districts.shp'
SENATE_DISTRICTS_PATH = 'data/shapefile/State_Senate'
INPUT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
OUTPUT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
POLL_BASELINE_FILE = 'poll_baseline.json'
DISTRICT_RESULTS_FILE = 'district_win_probabilities.json'


# ============================================================================
# LOAD DATA
# ============================================================================

def load_data():
    """Load all necessary data files"""
    print("\n" + "=" * 70)
    print("LOADING DATA")
    print("=" * 70)

    df = pd.read_csv(INPUT_CSV)

    # CREATE BACKUP WITH TIMESTAMP
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M")
    backup_path = INPUT_CSV.replace('.csv', f'_old_{timestamp}.csv')
    shutil.copy2(INPUT_CSV, backup_path)
    print(f"✓ Created backup: {backup_path}")

    # -----------------------------------------------------------------------
    # Read new versioned poll_baseline.json structure
    # All downstream data now lives under poll_data['current']
    # -----------------------------------------------------------------------
    with open(POLL_BASELINE_FILE, 'r') as f:
        poll_data = json.load(f)

    # Support both old (flat) and new (nested under 'current') structures
    if 'current' in poll_data:
        current = poll_data['current']
        print("✓ Detected versioned poll_baseline.json (reading from 'current')")
    else:
        current = poll_data
        print("⚠ Legacy poll_baseline.json detected (flat structure)")

    baseline_avg      = current['baseline']
    avg_moe           = current['avg_moe']
    scaled_crosstabs  = current.get('scaled_crosstabs')
    crosstab_moes     = current.get('crosstab_moes')
    fav_weights       = current.get('favorability_weights')
    senate_crosstabs  = current.get('senate_district_crosstabs')

    with open(DISTRICT_RESULTS_FILE, 'r') as f:
        district_data = json.load(f)
        target_median = district_data['median_results']

    print(f"✓ Loaded {len(df)} precincts")
    if scaled_crosstabs:
        print(f"✓ Loaded scaled crosstabs for demographic modeling")
    else:
        print(f"⚠ No crosstabs available, will use fallback geographic weights")
    if senate_crosstabs:
        sd_keys = list(senate_crosstabs.keys())
        print(f"✓ Loaded senate district crosstabs: {sd_keys}")
        if 'sd_other' in senate_crosstabs:
            print(f"  ✓ sd_other available for precincts outside SD-7/8/9")
        else:
            print(f"  ⚠ sd_other not found — outside precincts will use baseline")

    return df, baseline_avg, target_median, avg_moe, scaled_crosstabs, crosstab_moes, senate_crosstabs


# ============================================================================
# SENATE DISTRICT OVERLAP ENGINE
# ============================================================================

def build_senate_district_weights(df):
    """
    Spatially joins precincts to the three PPP senate districts (SD-7, SD-8, SD-9).

    For each precinct, calculates what fraction of its area falls within each
    of the three PPP senate districts. These fractions become mixing weights
    when blending senate-district-level crosstabs.

    Precincts that fall entirely outside all three districts are flagged with
    sd_outside_flag=True and will use the sd_other crosstab data (or the
    district-wide baseline if sd_other is unavailable).

    Returns df with columns appended:
        sd_weight_7, sd_weight_8, sd_weight_9, sd_outside_flag
    """
    print("\n" + "=" * 70)
    print("BUILDING SENATE DISTRICT OVERLAP WEIGHTS")
    print("=" * 70)

    # --- Load senate district shapefile ---
    try:
        gdf_senate = gpd.read_file(SENATE_DISTRICTS_PATH)
        print(f"✓ Loaded senate district shapefile ({len(gdf_senate)} districts)")
    except Exception as e:
        print(f"⚠ Could not load senate shapefile: {e}")
        print("  Falling back to district-wide baseline for all precincts")
        for sd in PPP_SENATE_DISTRICTS:
            df[f'sd_weight_{sd}'] = 0.0
        df['sd_outside_flag'] = True
        return df

    # Find the district number column
    dist_col = None
    for col in ['WIDNDISTRICT', 'DISTRICTCD', 'DISTRICTN', 'DISTRICT', 'DIST_NUM', 'DIST_NO', 'NAME']:
        if col in gdf_senate.columns:
            dist_col = col
            break

    if dist_col is None:
        print(f"  Available columns: {gdf_senate.columns.tolist()}")
        print("  ⚠ Could not identify district number column. Using baseline fallback.")
        for sd in PPP_SENATE_DISTRICTS:
            df[f'sd_weight_{sd}'] = 0.0
        df['sd_outside_flag'] = True
        return df

    print(f"  Using column '{dist_col}' for district IDs")
    print(f"  Sample values: {gdf_senate[dist_col].head(5).tolist()}")

    # Filter to the three PPP districts
    ppp_mask = gdf_senate[dist_col].astype(str).str.strip().isin(
        [str(d) for d in PPP_SENATE_DISTRICTS]
    )
    gdf_ppp = gdf_senate[ppp_mask].copy()
    print(f"  Found {len(gdf_ppp)} PPP senate district polygons "
          f"(expected {len(PPP_SENATE_DISTRICTS)})")

    if len(gdf_ppp) == 0:
        print("  ⚠ No PPP districts found. Check that district numbers match shapefile values.")
        print(f"  All unique values in {dist_col}: {sorted(gdf_senate[dist_col].unique().tolist())}")
        for sd in PPP_SENATE_DISTRICTS:
            df[f'sd_weight_{sd}'] = 0.0
        df['sd_outside_flag'] = True
        return df

    # --- Load precinct shapefile to get geometries ---
    try:
        gdf_precincts = gpd.read_file(SHAPEFILE_PATH)
        print(f"✓ Loaded precinct shapefile ({len(gdf_precincts)} precincts)")
    except Exception as e:
        print(f"  ⚠ Could not load precinct shapefile: {e}")
        for sd in PPP_SENATE_DISTRICTS:
            df[f'sd_weight_{sd}'] = 0.0
        df['sd_outside_flag'] = True
        return df

    # Align CRS
    if gdf_ppp.crs is None:
        gdf_ppp = gdf_ppp.set_crs(epsg=4326)
    if gdf_precincts.crs is None:
        gdf_precincts = gdf_precincts.set_crs(epsg=4326)
    if gdf_ppp.crs != gdf_precincts.crs:
        gdf_ppp = gdf_ppp.to_crs(gdf_precincts.crs)

    # Project to Illinois State Plane (EPSG:26916) for accurate area calculations
    gdf_precincts_proj = gdf_precincts.to_crs(epsg=26916)
    gdf_ppp_proj = gdf_ppp.to_crs(epsg=26916)

    # --- Initialize weight columns ---
    for sd in PPP_SENATE_DISTRICTS:
        df[f'sd_weight_{sd}'] = 0.0
    df['sd_outside_flag'] = False

    # Build a dict of senate district geometries keyed by district number
    sd_geoms = {}
    for _, row in gdf_ppp_proj.iterrows():
        sd_num = int(str(row[dist_col]).strip())
        sd_geoms[sd_num] = row.geometry

    # --- Match precinct CSV rows to shapefile geometries via JoinField ---
    join_col = 'JoinField'
    if join_col not in gdf_precincts.columns:
        for col in ['JOINFIELD', 'precinct_id', 'PRECINCT']:
            if col in gdf_precincts.columns:
                join_col = col
                break

    if join_col not in gdf_precincts.columns:
        print(f"  ⚠ Cannot find join column in precinct shapefile. "
              f"Columns: {gdf_precincts.columns.tolist()}")
        # Fall back: use positional index
        gdf_merged = gdf_precincts_proj.copy()
        use_index_join = True
    else:
        gdf_precincts_proj['JoinField_norm'] = gdf_precincts_proj[join_col].str.upper()
        df['JoinField_norm'] = df['JoinField'].str.upper()
        gdf_merged = df.merge(
            gdf_precincts_proj[['JoinField_norm', 'geometry']],
            on='JoinField_norm',
            how='left'
        )
        gdf_merged = gpd.GeoDataFrame(gdf_merged, geometry='geometry',
                                       crs=gdf_precincts_proj.crs)
        use_index_join = False

    n_matched = gdf_merged.geometry.notna().sum()
    print(f"\n  {n_matched}/{len(df)} precincts matched to shapefile geometries")
    print(f"  Calculating area overlaps with SD-{PPP_SENATE_DISTRICTS}...")

    # --- Calculate overlap fractions ---
    for idx, row in gdf_merged.iterrows():
        geom = row.geometry
        if geom is None or geom.is_empty:
            df.loc[idx, 'sd_outside_flag'] = True
            continue

        precinct_area = geom.area
        if precinct_area == 0:
            df.loc[idx, 'sd_outside_flag'] = True
            continue

        total_overlap = 0.0
        for sd_num, sd_geom in sd_geoms.items():
            try:
                overlap = geom.intersection(sd_geom).area
                df.loc[idx, f'sd_weight_{sd_num}'] = overlap / precinct_area
                total_overlap += overlap
            except Exception:
                pass

        # Flag precincts with less than 1% overlap with any PPP district
        if total_overlap / precinct_area < 0.01:
            df.loc[idx, 'sd_outside_flag'] = True

    # --- Summary ---
    outside_count = df['sd_outside_flag'].sum()
    inside_count = len(df) - outside_count
    print(f"\n  Precincts with PPP senate district coverage: {inside_count} "
          f"({inside_count/len(df)*100:.1f}%)")
    print(f"  Precincts outside all PPP districts (→ sd_other): {outside_count} "
          f"({outside_count/len(df)*100:.1f}%)")

    for sd in PPP_SENATE_DISTRICTS:
        avg_w = df[f'sd_weight_{sd}'].mean()
        nonzero = (df[f'sd_weight_{sd}'] > 0.01).sum()
        print(f"  SD-{sd}: avg overlap weight {avg_w:.3f}, "
              f"{nonzero} precincts with >1% overlap")

    return df



# ============================================================================
# SENATE DISTRICT CROSSTAB LOOKUP
# ============================================================================

def get_senate_district_support(cand, row, senate_crosstabs, baseline_avg):
    """
    Returns estimated support for a candidate in this precinct based on
    senate district crosstabs from the PPP poll.

    Logic:
    - If precinct is inside SD-7/8/9: area-weighted average of those districts
    - If precinct is OUTSIDE all three (sd_outside_flag=True): use sd_other data
    - If sd_other not available: return None (caller falls back to baseline)

    senate_crosstabs keys expected: 'sd_7', 'sd_8', 'sd_9', 'sd_other'
    """
    if not senate_crosstabs:
        return None

    outside = row.get('sd_outside_flag', True)

    # --- Outside all three PPP districts → use sd_other ---
    if outside:
        sd_other = senate_crosstabs.get('sd_other')
        if sd_other is None:
            return None
        support = sd_other.get(cand)
        return float(support) if support is not None else None

    # --- Inside at least one PPP district → area-weighted average ---
    total_weight = 0.0
    weighted_support = 0.0

    for sd in PPP_SENATE_DISTRICTS:
        w = row.get(f'sd_weight_{sd}', 0.0)
        if w < 0.01:
            continue

        sd_key = f'sd_{sd}'
        if sd_key not in senate_crosstabs:
            continue

        support = senate_crosstabs[sd_key].get(cand)
        if support is None:
            continue

        weighted_support += float(support) * w
        total_weight += w

    if total_weight < 0.01:
        return None

    return weighted_support / total_weight


# ============================================================================
# CROSSTAB HELPER FUNCTIONS
# ============================================================================

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
# STEP 1: APPLY DEMOGRAPHIC MODELING (Senate Districts + Crosstabs)
# ============================================================================

def apply_crosstab_modeling(df, baseline_avg, scaled_crosstabs, senate_crosstabs=None):
    """
    Apply demographic modeling to estimate precinct-level support.

    Priority order for each precinct:
      1. Senate district crosstabs (PPP SD-7/8/9/other) — most direct geographic signal
         - Inside SD-7/8/9: area-weighted average of overlapping districts
         - Outside SD-7/8/9: sd_other data
      2. Demographic crosstabs (ideology, age, race) — supplementary signal
      3. District-wide baseline — final fallback if nothing else available

    The senate district approach REPLACES the old hardcoded geographic boosts
    (Evanston Biss multiplier, Chicago Abughazaleh multiplier, Fine Chicago
    penalty, etc.) because the senate district crosstabs directly measure
    those same patterns from actual polling. The Evanston/Biss UNDECIDED
    penalty is preserved in Step 3 since undecided allocation is a separate
    behavioral signal not captured by the crosstabs.
    """
    print("\n" + "=" * 70)
    print("STEP 1: DEMOGRAPHIC MODELING (Senate Districts + Crosstabs)")
    print("=" * 70)

    use_senate = (senate_crosstabs is not None and any(
        f'sd_weight_{sd}' in df.columns for sd in PPP_SENATE_DISTRICTS
    ))

    if use_senate:
        n_inside = (~df['sd_outside_flag']).sum() if 'sd_outside_flag' in df.columns else '?'
        n_outside = df['sd_outside_flag'].sum() if 'sd_outside_flag' in df.columns else '?'
        has_other = 'sd_other' in senate_crosstabs
        print(f"  Senate district coverage: {n_inside} inside SD-7/8/9, "
              f"{n_outside} outside (→ {'sd_other' if has_other else 'baseline'})")
    else:
        print("  No senate district data — using demographic crosstabs only")

    # Ideology thresholds
    prog_scores = df['prog_score_imputed'].dropna()
    moderate_threshold    = prog_scores.quantile(0.333) if len(prog_scores) > 0 else -0.3
    somewhat_lib_threshold = prog_scores.quantile(0.667) if len(prog_scores) > 0 else  0.3

    print(f"\n  Ideology thresholds: moderate<={moderate_threshold:.3f}, "
          f"somewhat_lib<={somewhat_lib_threshold:.3f}")

    # Ensure demographic columns exist
    for col, default in [('median_voting_age', 50),
                          ('V_20_VAP_Black_pct', 0.0),
                          ('V_20_VAP_Asian_pct', 0.0)]:
        if col not in df.columns:
            df[col] = default

    # -----------------------------------------------------------------------
    # Calculate raw support for each candidate in each precinct
    # -----------------------------------------------------------------------
    for cand in CANDIDATES:
        district_avg = baseline_avg.get(cand, 0)
        precinct_support = []

        for idx, row in df.iterrows():
            support_components = []

            # SIGNAL 1: Senate district crosstabs (highest priority)
            if use_senate:
                sd_support = get_senate_district_support(
                    cand, row, senate_crosstabs, baseline_avg
                )
                if sd_support is not None:
                    support_components.append(('senate', sd_support, 2.0))

            # SIGNAL 2: Demographic crosstabs (ideology, age, race)
            if scaled_crosstabs and cand in scaled_crosstabs:
                crosstabs = scaled_crosstabs[cand]

                # Ideology
                prog_score = row.get('prog_score_imputed', 0)
                if prog_score <= moderate_threshold:
                    ideology_support = crosstabs.get('moderate', district_avg)
                elif prog_score <= somewhat_lib_threshold:
                    ideology_support = crosstabs.get('somewhat_liberal', district_avg)
                else:
                    ideology_support = crosstabs.get('very_liberal', district_avg)
                support_components.append(('ideology', ideology_support, 1.0))

                # Age
                age_support = map_age_to_crosstab(row.get('median_voting_age', 50), crosstabs)
                if age_support > 0:
                    support_components.append(('age', age_support, 1.0))

                # Race
                black_pct = row.get('V_20_VAP_Black_pct', 0)
                asian_pct = row.get('V_20_VAP_Asian_pct', 0)
                white_pct = max(0, 100 - black_pct - asian_pct)
                white_support = crosstabs.get('white', district_avg)

                black_support = (crosstabs['black'] if 'black' in crosstabs
                                 else white_support * 3.0 if cand == 'Simmons' and white_support > 0
                                 else district_avg * 3.0 if cand == 'Simmons'
                                 else white_support if white_support > 0
                                 else district_avg)

                asian_support = (crosstabs['asian'] if 'asian' in crosstabs
                                 else white_support * 2.5 if cand == 'Huynh' and white_support > 0
                                 else district_avg * 2.5 if cand == 'Huynh'
                                 else white_support * 0.8 if white_support > 0
                                 else district_avg * 0.8)

                racial_support = ((white_pct / 100) * white_support
                                  + (black_pct / 100) * black_support
                                  + (asian_pct / 100) * asian_support)
                support_components.append(('race', racial_support, 1.0))

            # SIGNAL 3: Fallback
            if not support_components:
                support_components.append(('baseline', district_avg, 1.0))

            total_weight = sum(w for _, _, w in support_components)
            avg_support = (sum(v * w for _, v, w in support_components) / total_weight
                           if total_weight > 0 else district_avg)

            precinct_support.append(avg_support)

        df[f'raw_{cand}'] = precinct_support

    # -----------------------------------------------------------------------
    # Diagnostics
    # -----------------------------------------------------------------------
    print("\n  Estimated support by region (before calibration):")
    for region_col, region_name in [('in_evanston', 'Evanston'), ('in_chicago', 'Chicago')]:
        if region_col in df.columns:
            mask = df[region_col] == 1
            if mask.sum() > 0:
                print(f"\n  {region_name} ({mask.sum()} precincts):")
                for c, v in sorted(
                    {c: df.loc[mask, f'raw_{c}'].mean() for c in CANDIDATES}.items(),
                    key=lambda x: -x[1]
                ):
                    print(f"    {c:<16}: {v:.1f}%")

    if use_senate and 'sd_outside_flag' in df.columns:
        outside = df[df['sd_outside_flag']]
        if len(outside) > 0:
            print(f"\n  Outside-district precincts using sd_other ({len(outside)}):")
            for c, v in sorted(
                {c: outside[f'raw_{c}'].mean() for c in CANDIDATES}.items(),
                key=lambda x: -x[1]
            ):
                print(f"    {c:<16}: {v:.1f}%")

    return df


# ============================================================================
# STEP 2: CALIBRATE TO DISTRICT BASELINE
# ============================================================================

def calibrate_to_baseline(df, baseline_avg, max_iterations=50, tolerance=0.5):
    print("\n" + "=" * 70)
    print("STEP 2: CALIBRATING TO DISTRICT BASELINE")
    print("=" * 70)

    total_turnout = df['estimated_turnout'].sum()

    for cand in CANDIDATES:
        df[f'adjusted_{cand}'] = df[f'raw_{cand}']

    for iteration in range(max_iterations):
        current_avg = {
            cand: (df[f'adjusted_{cand}'] * df['estimated_turnout']).sum() / total_turnout
            for cand in CANDIDATES
        }
        max_diff = max(abs(current_avg[c] - baseline_avg.get(c, 0)) for c in CANDIDATES)

        if max_diff < tolerance:
            print(f"✓ Converged after {iteration + 1} iterations (max diff: {max_diff:.3f}%)")
            break

        for cand in CANDIDATES:
            diff = baseline_avg.get(cand, 0) - current_avg[cand]
            df[f'adjusted_{cand}'] += diff
            df[f'adjusted_{cand}'] = np.maximum(df[f'adjusted_{cand}'], 0.1)
    else:
        print(f"⚠ Did not fully converge after {max_iterations} iterations")

    print("\nBaseline Calibration Results:")
    print(f"{'Candidate':<15s} {'Target':<10s} {'Achieved':<10s} {'Diff':<10s}")
    print("-" * 50)
    for cand in CANDIDATES:
        achieved = (df[f'adjusted_{cand}'] * df['estimated_turnout']).sum() / total_turnout
        diff = achieved - baseline_avg.get(cand, 0)
        print(f"{cand:<15s} {baseline_avg.get(cand, 0):>9.2f}% {achieved:>9.2f}% {diff:>9.2f}%")

    return df


# ============================================================================
# STEP 3: UNDECIDED ALLOCATION
# ============================================================================

def allocate_undecideds_crosstab_based(df, scaled_crosstabs, baseline_avg,
                                        senate_crosstabs=None):
    """
    Allocate undecided voters using senate district + crosstab-based weights.

    Evanston undecided penalty for Biss is preserved: the senate district
    crosstabs correctly model his decided-voter strength in Evanston, but
    undecideds in his own backyard are less likely to break for him
    (incumbency familiarity effect).
    """
    print("\n" + "=" * 70)
    print("STEP 3: ALLOCATING UNDECIDED VOTERS")
    print("=" * 70)

    prog_scores = df['prog_score_imputed'].dropna()
    moderate_threshold    = prog_scores.quantile(0.333) if len(prog_scores) > 0 else -0.3
    somewhat_lib_threshold = prog_scores.quantile(0.667) if len(prog_scores) > 0 else  0.3

    total_undecided_mass = 0
    evanston_undecided_mass = 0

    for idx, row in df.iterrows():
        decided_pct = sum(row[f'adjusted_{cand}'] for cand in CANDIDATES)
        undecided_pct = max(0, 100 - decided_pct)
        n_undecided = row['estimated_turnout'] * (undecided_pct / 100)
        total_undecided_mass += n_undecided
        if row.get('in_evanston', 0) == 1:
            evanston_undecided_mass += n_undecided

    print(f"Total undecided voters: {total_undecided_mass:.0f}")
    print(f"Evanston undecided voters: {evanston_undecided_mass:.0f} "
          f"({evanston_undecided_mass / total_undecided_mass * 100:.1f}%)")

    biss_evanston_penalty_effect = evanston_undecided_mass * (1 - BISS_EVANSTON_UNDECIDED_PENALTY)
    non_evanston_undecided_mass = total_undecided_mass - evanston_undecided_mass
    biss_non_evanston_boost = (1 + (biss_evanston_penalty_effect / non_evanston_undecided_mass)
                               if non_evanston_undecided_mass > 0 else 1.0)
    print(f"Biss non-Evanston undecided boost: {biss_non_evanston_boost:.3f}x")

    for idx, row in df.iterrows():
        decided_pct = sum(row[f'adjusted_{cand}'] for cand in CANDIDATES)
        undecided_pct = max(0, 100 - decided_pct)

        if undecided_pct == 0:
            for cand in CANDIDATES:
                df.loc[idx, f'final_{cand}'] = row[f'adjusted_{cand}']
            continue

        prog_score = row.get('prog_score_imputed', 0)
        median_age = row.get('median_voting_age', 50)
        black_pct  = row.get('V_20_VAP_Black_pct', 0)
        asian_pct  = row.get('V_20_VAP_Asian_pct', 0)
        white_pct  = max(0, 100 - black_pct - asian_pct)
        is_evanston = row.get('in_evanston', 0) == 1

        precinct_undecided_support = {}

        for cand in CANDIDATES:
            support_signals = []

            # Senate district signal
            if senate_crosstabs:
                sd_support = get_senate_district_support(
                    cand, row, senate_crosstabs, baseline_avg
                )
                if sd_support is not None:
                    support_signals.append(('senate', max(sd_support, 1.0), 2.0))

            # Demographic crosstab signal
            if scaled_crosstabs and cand in scaled_crosstabs:
                crosstabs = scaled_crosstabs[cand]

                if prog_score <= moderate_threshold:
                    ideo = crosstabs.get('moderate', 0)
                elif prog_score <= somewhat_lib_threshold:
                    ideo = crosstabs.get('somewhat_liberal', 0)
                else:
                    ideo = crosstabs.get('very_liberal', 0)
                support_signals.append(('ideology', ideo, 1.0))

                age_s = map_age_to_crosstab(median_age, crosstabs)
                support_signals.append(('age', age_s, 1.0))

                white_s = crosstabs.get('white', 0)
                black_s = (crosstabs['black'] if 'black' in crosstabs
                           else white_s * 3.0 if cand == 'Simmons' and white_s > 0
                           else 15.0 if cand == 'Simmons'
                           else white_s if white_s > 0 else 5.0)
                asian_s = (crosstabs['asian'] if 'asian' in crosstabs
                           else white_s * 2.5 if cand == 'Huynh' and white_s > 0
                           else 15.0 if cand == 'Huynh'
                           else white_s * 2.0 if cand == 'Amiwala' and white_s > 0
                           else 12.0 if cand == 'Amiwala'
                           else white_s * 0.8 if white_s > 0 else 5.0)

                racial_s = ((white_pct / 100) * white_s
                            + (black_pct / 100) * black_s
                            + (asian_pct / 100) * asian_s)
                support_signals.append(('race', racial_s, 1.0))

            if not support_signals:
                support_signals.append(('baseline', max(row[f'adjusted_{cand}'], 1.0), 1.0))

            total_w = sum(w for _, _, w in support_signals)
            avg_s = (sum(v * w for _, v, w in support_signals) / total_w
                     if total_w > 0 else 1.0)
            precinct_undecided_support[cand] = max(avg_s, 1.0)

            # Biss Evanston undecided modifier
            if cand == 'Biss':
                if is_evanston:
                    precinct_undecided_support[cand] *= BISS_EVANSTON_UNDECIDED_PENALTY
                else:
                    precinct_undecided_support[cand] *= biss_non_evanston_boost

        # Normalize
        total_support = sum(precinct_undecided_support.values())
        if total_support > 0:
            for cand in CANDIDATES:
                precinct_undecided_support[cand] /= total_support
        else:
            for cand in CANDIDATES:
                precinct_undecided_support[cand] = 1.0 / len(CANDIDATES)

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
    print("\n" + "=" * 70)
    print("STEP 4: FINAL CALIBRATION TO TARGET MEDIAN")
    print("=" * 70)

    total_turnout = df['estimated_turnout'].sum()

    for iteration in range(max_iterations):
        current_avg = {
            cand: (df[f'final_{cand}'] * df['estimated_turnout']).sum() / total_turnout
            for cand in CANDIDATES
        }
        max_diff = max(abs(current_avg[c] - target_median.get(c, 0)) for c in CANDIDATES)

        if max_diff < tolerance:
            print(f"✓ Converged after {iteration + 1} iterations (max diff: {max_diff:.3f}%)")
            break

        for cand in CANDIDATES:
            diff = target_median.get(cand, 0) - current_avg[cand]
            df[f'final_{cand}'] += diff * 0.3
            df[f'final_{cand}'] = np.maximum(df[f'final_{cand}'], 0.1)

    print("\nFinal Calibration:")
    print(f"{'Candidate':<15s} {'Target':<10s} {'Achieved':<10s} {'Diff':<10s}")
    print("-" * 50)
    for cand in CANDIDATES:
        achieved = (df[f'final_{cand}'] * df['estimated_turnout']).sum() / total_turnout
        diff = achieved - target_median.get(cand, 0)
        print(f"{cand:<15s} {target_median.get(cand, 0):>9.2f}% {achieved:>9.2f}% {diff:>9.2f}%")

    return df


# ============================================================================
# STEP 5: MONTE CARLO SIMULATIONS
# ============================================================================

def run_precinct_monte_carlo(df, avg_moe):
    print("\n" + "=" * 70)
    print(f"STEP 5: RUNNING {N_SIMULATIONS:,} MONTE CARLO SIMULATIONS")
    print("=" * 70)

    n_precincts = len(df)
    n_candidates = len(CANDIDATES)

    baselines = np.zeros((n_precincts, n_candidates))
    for i, cand in enumerate(CANDIDATES):
        baselines[:, i] = df[f'final_{cand}'].values
    baselines = baselines / 100

    MODERATES         = ['Fine', 'Andrew']
    BISS_GROUP        = ['Biss']
    OTHER_PROGRESSIVES = ['Abughazaleh', 'Simmons', 'Amiwala', 'Huynh']

    ideological_errors = np.random.normal(0, MOE_DISTRICT * 0.01 * 0.7,
                                           size=(N_SIMULATIONS, 3))
    individual_noise   = np.random.normal(0, MOE_DISTRICT * 0.01 * 0.3,
                                           size=(N_SIMULATIONS, n_candidates))

    district_noise = np.zeros((N_SIMULATIONS, n_candidates))
    for i, cand in enumerate(CANDIDATES):
        if cand in MODERATES:
            district_noise[:, i] = ideological_errors[:, 0] + individual_noise[:, i]
        elif cand in BISS_GROUP:
            district_noise[:, i] = ideological_errors[:, 1] + individual_noise[:, i]
        elif cand in OTHER_PROGRESSIVES:
            district_noise[:, i] = ideological_errors[:, 2] + individual_noise[:, i]

    local_noise = np.random.normal(0, MOE_PRECINCT * 0.01,
                                    size=(N_SIMULATIONS, n_precincts, n_candidates))

    simulated_pcts = (baselines[np.newaxis, :, :]
                      + district_noise[:, np.newaxis, :]
                      + local_noise)
    simulated_pcts = np.maximum(simulated_pcts, 0)
    simulated_pcts = simulated_pcts / simulated_pcts.sum(axis=2, keepdims=True)

    winners_idx = np.argmax(simulated_pcts, axis=2)
    turnout = df['estimated_turnout'].values

    for i, cand in enumerate(CANDIDATES):
        wins       = (winners_idx == i).sum(axis=0)
        win_prob   = wins / N_SIMULATIONS
        median_pct = np.median(simulated_pcts[:, :, i], axis=0) * 100
        median_votes = np.round(median_pct / 100 * turnout).astype(int)

        df[f'win_prob_{cand}']   = win_prob
        df[f'median_pct_{cand}'] = median_pct
        df[f'median_votes_{cand}'] = median_votes

    print("✓ Simulations complete")
    return df


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("PRECINCT-LEVEL MONTE CARLO SIMULATOR V4")
    print("Senate District Crosstab Integration (SD-7/8/9 + sd_other)")
    print("=" * 70)

    df, baseline_avg, target_median, avg_moe, scaled_crosstabs, \
        crosstab_moes, senate_crosstabs = load_data()

    # Build senate district overlap weights (spatial join to shapefile)
    df = build_senate_district_weights(df)
    df = build_senate_district_weights(df)

    # --- TEMPORARY DIAGNOSTIC ---
    import geopandas as gpd
    gdf_senate = gpd.read_file(SENATE_DISTRICTS_PATH)
    print("\n=== SENATE SHAPEFILE DEBUG ===")
    print(f"Columns: {gdf_senate.columns.tolist()}")
    print(f"CRS: {gdf_senate.crs}")
    for col in gdf_senate.columns:
        print(f"  {col}: {gdf_senate[col].head(5).tolist()}")
    print(f"\nsd_weight_7 nonzero: {(df['sd_weight_7'] > 0.01).sum()}")
    print(f"sd_weight_8 nonzero: {(df['sd_weight_8'] > 0.01).sum()}")
    print(f"sd_weight_9 nonzero: {(df['sd_weight_9'] > 0.01).sum()}")
    print(f"sd_outside_flag True: {df['sd_outside_flag'].sum()}")
    n_geom_matched = df['JoinField_norm'].isin(
        gpd.read_file(SHAPEFILE_PATH)['JoinField'].str.upper()
    ).sum() if 'JoinField_norm' in df.columns else 'N/A'
    print(f"JoinField matches: {n_geom_matched}/{len(df)}")
    # --- END DIAGNOSTIC ---
    # Step 1: Apply modeling (senate districts take priority over old boosts)
    df = apply_crosstab_modeling(df, baseline_avg, scaled_crosstabs, senate_crosstabs)

    # Step 2: Calibrate to baseline
    df = calibrate_to_baseline(df, baseline_avg)

    # Step 3: Allocate undecideds
    df = allocate_undecideds_crosstab_based(df, scaled_crosstabs, baseline_avg, senate_crosstabs)

    # Step 4: Final calibration
    df = final_calibrate(df, target_median)

    # Step 5: Monte Carlo
    df = run_precinct_monte_carlo(df, avg_moe)

    # Save results
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\n✓ Full results saved to {OUTPUT_CSV}")

    # Simplified output
    simplified_columns = ['JoinField', 'JoinFieldAlt', 'estimated_turnout']
    for cand in CANDIDATES:
        simplified_columns.extend([
            f'win_prob_{cand}', f'median_pct_{cand}', f'median_votes_{cand}'
        ])
    available_columns = [c for c in simplified_columns if c in df.columns]
    df_simplified = df[available_columns].copy()
    for cand in CANDIDATES:
        pct_col = f'median_pct_{cand}'
        if pct_col in df_simplified.columns:
            df_simplified[pct_col] = df_simplified[pct_col] / 100

    simplified_path = OUTPUT_CSV.replace('.csv', '_simplified.csv')
    df_simplified.to_csv(simplified_path, index=False)
    print(f"✓ Simplified results saved to {simplified_path}")

    # Geographic variation check
    print("\n" + "=" * 70)
    print("GEOGRAPHIC VARIATION CHECK")
    print("=" * 70)

    for region_mask, region_name in [
        (df.get('in_evanston', pd.Series(0, index=df.index)) == 1, 'Evanston'),
        (df.get('in_chicago',  pd.Series(0, index=df.index)) == 1, 'Chicago'),
    ]:
        if region_mask.sum() > 0:
            print(f"\n{region_name} (n={region_mask.sum()}):")
            for cand in sorted(CANDIDATES,
                               key=lambda c: -df.loc[region_mask, f'median_pct_{cand}'].median()):
                val = df.loc[region_mask, f'median_pct_{cand}'].median()
                if val > 2:
                    print(f"  {cand:<16}: {val:.1f}%")

    # Senate district breakdown
    for sd in PPP_SENATE_DISTRICTS:
        col = f'sd_weight_{sd}'
        if col in df.columns:
            sd_df = df[df[col] > 0.5]
            if len(sd_df) > 0:
                print(f"\nSD-{sd} majority precincts (n={len(sd_df)}):")
                for cand in sorted(CANDIDATES,
                                   key=lambda c: -sd_df[f'median_pct_{c}'].median()):
                    val = sd_df[f'median_pct_{cand}'].median()
                    if val > 3:
                        print(f"  {cand:<16}: {val:.1f}%")

    outside = df[df.get('sd_outside_flag', pd.Series(False, index=df.index))]
    if len(outside) > 0:
        print(f"\nOutside-district precincts using sd_other (n={len(outside)}):")
        for cand in sorted(CANDIDATES,
                           key=lambda c: -outside[f'median_pct_{c}'].median()):
            val = outside[f'median_pct_{cand}'].median()
            if val > 3:
                print(f"  {cand:<16}: {val:.1f}%")

    print("\n" + "=" * 70)
    print("SIMULATION COMPLETE!")
    print("=" * 70)
    print(f"\nFiles created:")
    print(f"  - Full dataset:  {OUTPUT_CSV}")
    print(f"  - Simplified:    {simplified_path}")


if __name__ == "__main__":
    main()