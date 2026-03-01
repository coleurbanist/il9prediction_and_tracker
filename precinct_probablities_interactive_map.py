import geopandas as gpd
import pandas as pd
import json
import plotly.graph_objects as go
from shapely.ops import unary_union
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

SHAPEFILE_PATH = 'data/shapefile/IL24/IL24.shp'
CONGRESSIONAL_DISTRICTS_PATH = 'data/shapefile/congressional_districts.shp'
PRECINCT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
DISTRICT_PROBS_JSON = 'district_win_probabilities.json'
POLL_BASELINE_FILE = 'poll_baseline.json'
VOTES_CSV = 'data/csv_data/votes.csv'            # Region × date cumulative vote totals
REGIONAL_FORECAST_FILE = 'regional_vote_forecast.json'  # fallback if votes.csv absent
OUTPUT_HTML = 'IL09_precinct_map.html'

CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']

# Map votes.csv row labels → model region keys used in regional_vote_forecast.json
VOTES_CSV_REGION_MAP = {
    'Cook County':      'Suburban Cook',
    'City of Chicago':  'Chicago',
    'Lake County':      'Lake County',
    'McHenry County':   'McHenry County',
}

# Color mapping
COLORS = {
    'Fine':        'green',
    'Abughazaleh': 'orange',
    'Biss':        'purple',
    'Amiwala':     'turquoise',
    'Simmons':     'deeppink',
    'Andrew':      'red',
    'Huynh':       'gray',
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def sort_candidates_by_prob_then_vote(row):
    return sorted(
        [{'candidate': c, 'win_prob': row[f'win_prob_{c}'], 'median_pct': row[f'median_pct_{c}']}
         for c in CANDIDATES],
        key=lambda x: (x['win_prob'], x['median_pct']),
        reverse=True
    )


def get_sorted_probabilities(row):
    ranked = sort_candidates_by_prob_then_vote(row)
    return [(r['candidate'], r['win_prob'], r['median_pct']) for r in ranked]


def calculate_competitiveness(row):
    probs = sorted([row[f'win_prob_{c}'] for c in CANDIDATES], reverse=True)
    return probs[0] - probs[1]


def assign_region(row):
    if row.get('in_chicago', 0) == 1:
        return 'Chicago'
    elif row.get('in_evanston', 0) == 1:
        return 'Evanston'
    elif row.get('in_lake', 0) == 1:
        return 'Lake County'
    elif row.get('in_mchenry', 0) == 1:
        return 'McHenry County'
    elif row.get('in_cook', 0) == 1:
        return 'Suburban Cook (not including Evanston)'
    else:
        return 'Other'


# ============================================================================
# BANKED VOTE ENGINE
# Uses votes.csv (cumulative) + poll_baseline.json history to distribute
# each batch of votes using the polling baseline closest in time.
# ============================================================================

def parse_votes_csv_date(col_str):
    """
    Parse date strings like '17-Feb', '19-Feb', '26-Feb' into datetime objects.
    Assumes year 2026.
    """
    try:
        return datetime.strptime(col_str.strip() + '-2026', '%d-%b-%Y')
    except ValueError:
        return None


def get_snapshot_for_date(history, target_date):
    """
    Return the most recent history snapshot with as_of <= target_date.
    Falls back to the earliest snapshot if all are after target_date.

    history: list of dicts each with 'as_of' key (YYYY-MM-DD string)
    target_date: datetime object
    """
    best = None
    best_date = None

    for snap in history:
        snap_date = datetime.strptime(snap['as_of'], '%Y-%m-%d')
        if snap_date <= target_date:
            if best_date is None or snap_date > best_date:
                best = snap
                best_date = snap_date

    # If no snapshot is on or before target_date, use the earliest one
    if best is None and history:
        best = min(history, key=lambda s: s['as_of'])

    return best


def compute_banked_votes(poll_data, votes_csv_path, regional_forecast_data):
    """
    Reads votes.csv and distributes each batch of newly-cast votes using the
    polling baseline from the closest-in-time history snapshot.

    Logic:
    1. Parse votes.csv: rows=regions, columns=dates (cumulative)
    2. For each date column, compute the new batch = cumulative[date] - cumulative[prev_date]
    3. Find the poll_baseline.json history snapshot with as_of <= batch_date
    4. Use that snapshot's regional vote shares (from regional_forecast_data) and
       district-level baseline to estimate candidate distribution within each region
    5. Accumulate across all batches and regions

    Returns:
        banked_by_region: { region_key: { 'cast': int, 'by_candidate': {cand: int} } }
        district_banked:  { cand: int }
        batch_log:        list of dicts for display/debugging
    """
    # --- Load history from poll_baseline.json ---
    history = poll_data.get('history', [])
    if not history:
        print("  ⚠ No history snapshots in poll_baseline.json — using current baseline for all batches")
        # Wrap current snapshot as a single-entry history
        current = poll_data.get('current', poll_data)
        history = [{'as_of': current.get('as_of', '2026-01-01'), 'baseline': current.get('baseline', {})}]

    # --- Load votes.csv ---
    try:
        df_votes = pd.read_csv(votes_csv_path, index_col=0)
        print(f"  ✓ Loaded votes.csv: {df_votes.shape[0]} regions × {df_votes.shape[1]} dates")
    except FileNotFoundError:
        print(f"  ⚠ {votes_csv_path} not found — banked vote section will be skipped")
        return None, None, None

    # Parse date columns
    date_cols = []
    for col in df_votes.columns:
        dt = parse_votes_csv_date(col)
        if dt is not None:
            date_cols.append((col, dt))
        else:
            print(f"  ⚠ Could not parse date column: '{col}' — skipping")

    if not date_cols:
        print("  ⚠ No parseable date columns in votes.csv")
        return None, None, None

    date_cols.sort(key=lambda x: x[1])  # sort chronologically

    # --- Accumulate banked votes ---
    banked_by_region = {r: {'cast': 0, 'by_candidate': {c: 0 for c in CANDIDATES}}
                        for r in VOTES_CSV_REGION_MAP.values()}
    district_banked = {c: 0 for c in CANDIDATES}
    batch_log = []

    # Previous cumulative totals per region (for computing incremental batches)
    prev_cumulative = {row_label: 0 for row_label in df_votes.index}

    for col_str, batch_date in date_cols:
        # Find the appropriate history snapshot for this batch
        snap = get_snapshot_for_date(history, batch_date)
        snap_baseline = snap.get('baseline', {}) if snap else {}
        snap_as_of = snap.get('as_of', 'unknown') if snap else 'unknown'

        batch_total = 0
        batch_by_region = {}

        for row_label in df_votes.index:
            model_region = VOTES_CSV_REGION_MAP.get(str(row_label).strip())
            if model_region is None:
                continue  # skip Total row or unrecognized regions

            cumul = df_votes.loc[row_label, col_str]
            try:
                cumul = int(cumul)
            except (ValueError, TypeError):
                continue

            new_votes = max(0, cumul - prev_cumulative.get(row_label, 0))
            prev_cumulative[row_label] = cumul
            batch_total += new_votes

            if new_votes == 0:
                batch_by_region[model_region] = {'new_votes': 0, 'by_candidate': {c: 0 for c in CANDIDATES}}
                continue

            # Distribute new_votes using regional forecast shares adjusted by
            # the snapshot baseline. If we have regional forecast data, use its
            # vote_shares for this region; otherwise fall back to district baseline.
            rdata = regional_forecast_data.get(model_region, {}) if regional_forecast_data else {}
            regional_shares = rdata.get('vote_shares', {})

            # Build distribution weights:
            # - If regional_shares available, use them (they encode geographic variation)
            # - Rescale to match the snapshot's district-level baseline ratios
            dist_weights = {}
            if regional_shares and snap_baseline:
                # Scale regional shares by snapshot baseline (relative to a reference baseline)
                # This adjusts for polling movement while preserving geographic patterns
                total_dist = sum(snap_baseline.get(c, 0) for c in CANDIDATES)
                total_reg  = sum(regional_shares.get(c, 0) for c in CANDIDATES)

                for cand in CANDIDATES:
                    reg_share  = regional_shares.get(cand, 0)
                    dist_share = snap_baseline.get(cand, 0)

                    if total_reg > 0 and total_dist > 0:
                        # Blend: 60% regional pattern, 40% snapshot baseline
                        blended = 0.6 * (reg_share / total_reg) + 0.4 * (dist_share / total_dist)
                    elif total_dist > 0:
                        blended = dist_share / total_dist
                    else:
                        blended = 1.0 / len(CANDIDATES)

                    dist_weights[cand] = max(blended, 0)

            elif snap_baseline:
                # No regional data — use snapshot baseline directly
                total_dist = sum(snap_baseline.get(c, 0) for c in CANDIDATES)
                for cand in CANDIDATES:
                    dist_weights[cand] = (snap_baseline.get(cand, 0) / total_dist
                                          if total_dist > 0 else 1.0 / len(CANDIDATES))
            else:
                # No data at all — uniform
                for cand in CANDIDATES:
                    dist_weights[cand] = 1.0 / len(CANDIDATES)

            # Normalize weights
            total_w = sum(dist_weights.values())
            if total_w > 0:
                dist_weights = {c: w / total_w for c, w in dist_weights.items()}

            # Allocate votes
            cand_votes = {c: round(new_votes * dist_weights[c]) for c in CANDIDATES}
            # Correct rounding error on largest candidate
            diff = new_votes - sum(cand_votes.values())
            if diff != 0:
                top_cand = max(CANDIDATES, key=lambda c: dist_weights[c])
                cand_votes[top_cand] += diff

            # Accumulate
            banked_by_region[model_region]['cast'] += new_votes
            for cand in CANDIDATES:
                banked_by_region[model_region]['by_candidate'][cand] += cand_votes[cand]
                district_banked[cand] += cand_votes[cand]

            batch_by_region[model_region] = {'new_votes': new_votes, 'by_candidate': cand_votes}

        batch_log.append({
            'date': col_str,
            'date_parsed': batch_date.strftime('%Y-%m-%d'),
            'snapshot_used': snap_as_of,
            'new_votes': batch_total,
            'cumulative': sum(prev_cumulative.values()),
            'by_region': batch_by_region,
        })

        print(f"  {col_str}: +{batch_total:,} votes → using snapshot as_of {snap_as_of}")

    return banked_by_region, district_banked, batch_log


# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")

gdf = gpd.read_file(SHAPEFILE_PATH)
print(f"✓ Loaded {len(gdf)} precincts from shapefile")

gdf_congress = gpd.read_file(CONGRESSIONAL_DISTRICTS_PATH)
print(f"✓ Loaded {len(gdf_congress)} congressional districts")

df_probs = pd.read_csv(PRECINCT_CSV)
print(f"✓ Loaded {len(df_probs)} precincts from CSV")

with open(DISTRICT_PROBS_JSON, 'r') as f:
    district_data = json.load(f)
    district_win_probs = district_data['win_probabilities']
    district_median    = district_data['median_results']
    district_sim_wins  = district_data.get('simulation_wins', {})
print("✓ Loaded district-wide probabilities")

# Load versioned poll_baseline.json (new structure under 'current')
with open(POLL_BASELINE_FILE, 'r') as f:
    poll_data = json.load(f)

if 'current' in poll_data:
    baseline_avg = poll_data['current']['baseline']
    print("✓ Loaded baseline poll average (versioned structure)")
else:
    baseline_avg = poll_data.get('baseline', {})
    print("✓ Loaded baseline poll average (legacy structure)")

# Load regional forecast (used as geographic distribution anchor for banked votes)
try:
    with open(REGIONAL_FORECAST_FILE, 'r') as f:
        regional_forecast = json.load(f)
    regional_forecast_data = regional_forecast.get('regions', {})
    print(f"✓ Loaded regional vote forecast")
except FileNotFoundError:
    regional_forecast_data = {}
    print(f"⚠ {REGIONAL_FORECAST_FILE} not found — banked votes will use district baseline only")

# ============================================================================
# EXTRACT IL-09 BOUNDARY AND CLIP PRECINCTS
# ============================================================================

print("\nExtracting IL-09 congressional district boundary...")

if gdf_congress.crs is None:
    gdf_congress = gdf_congress.set_crs(epsg=4326)
if gdf.crs is None:
    gdf = gdf.set_crs(epsg=4326)
if gdf_congress.crs != gdf.crs:
    gdf_congress = gdf_congress.to_crs(gdf.crs)

district_col = None
for col in ['DISTRICT', 'CD', 'CONG_DIST', 'DIST_NUM', 'NAME', 'NAMELSAD']:
    if col in gdf_congress.columns:
        district_col = col
        break

if district_col is None:
    print("  ERROR: Could not identify district number column")
    exit(1)

il09_mask = (
    (gdf_congress[district_col] == '09') |
    (gdf_congress[district_col] == '9')  |
    (gdf_congress[district_col] == 9)    |
    (gdf_congress[district_col].astype(str).str.contains('09', na=False)) |
    (gdf_congress[district_col].astype(str).str.contains('9', na=False))
)

if il09_mask.sum() == 0:
    print("  ERROR: Could not find district 9")
    exit(1)

il09_geom = gdf_congress[il09_mask].geometry.unary_union
gdf['geometry'] = gdf.geometry.intersection(il09_geom)
gdf = gdf[~gdf.geometry.is_empty].copy()
print(f"✓ Clipped {len(gdf)} precincts to IL-09 boundaries")

# ============================================================================
# MULTI-STRATEGY JOIN
# ============================================================================

print("Joining precinct shapefile to CSV data...")

gdf['JoinField_norm']      = gdf['JoinField'].str.upper()
df_probs['JoinField_norm'] = df_probs['JoinField'].str.upper()
df_probs['JoinField2_norm']   = df_probs['JoinField2'].str.upper()
df_probs['JoinFieldAlt_norm'] = df_probs['JoinFieldAlt'].str.upper()

gdf_merged = gdf.merge(df_probs, on='JoinField_norm', how='inner',
                        suffixes=('_shape', '_csv'))
print(f"  Strategy 1 (JoinField): {len(gdf_merged)} matches")

for strat_num, right_col in [(2, 'JoinField2_norm'), (3, 'JoinFieldAlt_norm')]:
    unmatched_shape = gdf[~gdf['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]
    unmatched_csv   = df_probs[~df_probs['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]
    if len(unmatched_shape) > 0 and len(unmatched_csv) > 0:
        extra = unmatched_shape.merge(unmatched_csv, left_on='JoinField_norm',
                                       right_on=right_col, how='inner',
                                       suffixes=('_shape', '_csv'))
        if len(extra) > 0:
            print(f"  Strategy {strat_num} ({right_col}): {len(extra)} additional matches")
            gdf_merged = pd.concat([gdf_merged, extra], ignore_index=True)

print(f"✓ Total merged: {len(gdf_merged)} precincts")

gdf_merged = gpd.GeoDataFrame(gdf_merged, geometry='geometry')
if gdf_merged.crs is None:
    gdf_merged = gdf_merged.set_crs(epsg=4326)
elif gdf_merged.crs != 'EPSG:4326':
    gdf_merged = gdf_merged.to_crs(epsg=4326)

invalid = ~gdf_merged.geometry.is_valid
if invalid.sum() > 0:
    gdf_merged.loc[invalid, 'geometry'] = gdf_merged.loc[invalid, 'geometry'].buffer(0)

empty = gdf_merged.geometry.is_empty
if empty.sum() > 0:
    gdf_merged = gdf_merged[~empty]

print(f"✓ Final dataset: {len(gdf_merged)} precincts ready for mapping")

# ============================================================================
# PRECINCT WINNERS AND REGIONS
# ============================================================================

gdf_merged['winner'] = gdf_merged.apply(
    lambda row: sort_candidates_by_prob_then_vote(row)[0]['candidate'], axis=1)
gdf_merged['winner_color'] = gdf_merged['winner'].map(COLORS)
gdf_merged['competitiveness_margin'] = gdf_merged.apply(calculate_competitiveness, axis=1)

df_probs['region']  = df_probs.apply(assign_region, axis=1)
gdf_merged['region'] = gdf_merged.apply(assign_region, axis=1)

# ============================================================================
# REGIONAL STATISTICS
# ============================================================================

regions = ['Chicago', 'Evanston', 'Suburban Cook (not including Evanston)',
           'Lake County', 'McHenry County']
regional_stats = {}
total_turnout = df_probs['estimated_turnout'].sum()

for region in regions:
    region_df = df_probs[df_probs['region'] == region]
    if len(region_df) == 0:
        continue
    region_turnout = region_df['estimated_turnout'].sum()
    candidate_shares = {
        cand: ((region_df[f'median_pct_{cand}'] * region_df['estimated_turnout']).sum()
               / region_turnout if region_turnout > 0 else 0)
        for cand in CANDIDATES
    }
    regional_stats[region] = {
        'turnout_pct':      (region_turnout / total_turnout) * 100,
        'candidate_shares': candidate_shares,
        'num_precincts':    len(region_df),
    }

# ============================================================================
# REGIONAL BOUNDARY OUTLINES
# ============================================================================

regional_boundaries = {}
for region in regions:
    region_precincts = gdf_merged[gdf_merged['region'] == region]
    if len(region_precincts) > 0:
        regional_boundaries[region] = gpd.GeoDataFrame(
            {'region': [region]},
            geometry=[region_precincts.geometry.unary_union],
            crs=gdf_merged.crs
        )

competitive_precincts = gdf_merged.nsmallest(10, 'competitiveness_margin')

# ============================================================================
# HOVER TEXT
# ============================================================================

def create_hover_text(row):
    region = row.get('region', 'Unknown')
    precinct_name = row.get('precinct_name',
                             row.get('JoinField_csv', row.get('JoinField_shape', 'Unknown')))
    ranked = sort_candidates_by_prob_then_vote(row)
    winner = ranked[0]['candidate']
    margin = ranked[0]['median_pct'] - (ranked[1]['median_pct'] if len(ranked) > 1 else 0)
    turnout = row.get('estimated_turnout', 0)

    lines = [
        f"<b>Region: {region}</b><br>",
        f"<b>Precinct: {precinct_name}</b><br>",
        "<span style='font-family: monospace'>",
        "Candidate        Win%    Vote%<br>",
        "-------------------------------<br>",
    ]
    for r in ranked:
        lines.append(f"{r['candidate']:<14} {r['win_prob']*100:>5.1f}%  {r['median_pct']:>6.1f}%<br>")
    lines += [
        "-------------------------------<br>",
        f"<b>Expected Winner: {winner}</b><br>",
        f"<b>Margin: {margin:>6.1f} pts</b><br>",
        f"<b>Expected Turnout: {int(turnout):,}</b><br>",
        "</span>",
    ]
    return "".join(lines)

gdf_merged['hover_text'] = gdf_merged.apply(create_hover_text, axis=1)

# ============================================================================
# BUILD PLOTLY MAP
# ============================================================================

print("Creating interactive map...")
fig = go.Figure()

for cand in CANDIDATES:
    mask = gdf_merged['winner'] == cand
    if mask.sum() > 0:
        gdf_subset = gdf_merged[mask].copy()
        gdf_subset['id'] = range(len(gdf_subset))
        fig.add_trace(go.Choroplethmapbox(
            geojson=gdf_subset.__geo_interface__,
            locations=gdf_subset['id'],
            z=[1] * len(gdf_subset),
            colorscale=[[0, COLORS[cand]], [1, COLORS[cand]]],
            showscale=False,
            marker_line_width=0.5,
            marker_line_color='white',
            marker_opacity=0.6,
            text=gdf_subset['hover_text'],
            hovertemplate='%{text}<extra></extra>',
            name=f'{cand} ({mask.sum()} precincts)',
            featureidkey="properties.id"
        ))

for region, gdf_region in regional_boundaries.items():
    geom = gdf_region.geometry.iloc[0]
    polygons = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
    for poly in polygons:
        coords = list(poly.exterior.coords)
        fig.add_trace(go.Scattermapbox(
            lon=[c[0] for c in coords], lat=[c[1] for c in coords],
            mode='lines', line=dict(width=3, color='black'),
            hoverinfo='skip', showlegend=False
        ))

gdf_proj = gdf_merged.to_crs(epsg=3857)
center = gpd.GeoSeries([gdf_proj.geometry.unary_union.centroid], crs=3857).to_crs(4326)[0]

fig.update_layout(
    mapbox=dict(style="open-street-map", zoom=9.5,
                center=dict(lat=center.y, lon=center.x)),
    margin={"r": 0, "t": 50, "l": 0, "b": 0},
    title={'text': 'IL-09 Democratic Primary', 'x': 0.5,
           'xanchor': 'center', 'font': {'size': 24}},
    height=800,
    showlegend=True,
    legend=dict(title="Most Likely Winner", yanchor="top", y=0.99,
                xanchor="left", x=0.01, bgcolor="rgba(255,255,255,0.9)")
)

# ============================================================================
# BANKED VOTE CALCULATION
# ============================================================================

print("\nCalculating banked votes from votes.csv...")
banked_by_region, district_banked, batch_log = compute_banked_votes(
    poll_data, VOTES_CSV, regional_forecast_data
)

# ============================================================================
# BUILD STATS HTML
# ============================================================================

sorted_district = sorted(district_win_probs.items(), key=lambda x: x[1], reverse=True)
sorted_baseline = sorted(baseline_avg.items(), key=lambda x: x[1], reverse=True)
total_sims = sum(district_sim_wins.values()) if district_sim_wins else 100_000

stats_html = f"""
<div style="max-width: 1400px; margin: 20px auto; padding: 20px; font-family: Arial, sans-serif;">

    <!-- Color Key -->
    <div style="margin-bottom: 30px; padding: 20px; background-color: #f9f9f9; border-radius: 8px;">
        <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.3rem;">
            Candidate Color Key
        </h2>
        <div style="display: flex; flex-wrap: wrap; justify-content: center; gap: 15px; margin-top: 20px;">
"""
for cand in CANDIDATES:
    stats_html += f"""
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 30px; height: 30px; background-color: {COLORS[cand]}; border: 2px solid #333; border-radius: 4px;"></div>
                <span style="font-weight: bold; font-size: 1rem;">{cand}</span>
            </div>
"""

stats_html += """
        </div>
    </div>

    <!-- District-Wide Tables -->
    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; justify-items: center; margin-bottom: 40px;">

        <!-- Win Probabilities -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                District-Wide Win Probabilities
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead><tr style="background-color: #f0f0f0;">
                    <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                    <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Win Prob.</th>
                </tr></thead><tbody>
"""
for cand, prob in sorted_district:
    stats_html += f"""
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{prob:.1f}%</td></tr>
"""
stats_html += """        </tbody></table></div>

        <!-- Poll Average -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                Weighted Poll Average
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead><tr style="background-color: #f0f0f0;">
                    <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                    <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Poll Avg</th>
                </tr></thead><tbody>
"""
for cand, pct in sorted_baseline:
    if cand in CANDIDATES:
        stats_html += f"""
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{pct:.1f}%</td></tr>
"""
stats_html += """        </tbody></table></div>

        <!-- Projected Results -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                Projected Results
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead><tr style="background-color: #f0f0f0;">
                    <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                    <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Vote Share</th>
                </tr></thead><tbody>
"""
for cand, prob in sorted_district:
    stats_html += f"""
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{district_median[cand]:.1f}%</td></tr>
"""
stats_html += f"""        </tbody></table></div>

        <!-- Simulations Won -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                Simulations Won
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead><tr style="background-color: #f0f0f0;">
                    <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                    <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Wins</th>
                </tr></thead><tbody>
"""
for cand, wins in sorted(district_sim_wins.items(), key=lambda x: x[1], reverse=True):
    if cand in CANDIDATES:
        stats_html += f"""
                <tr><td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{wins:,}</td></tr>
"""
stats_html += f"""        </tbody></table>
            <p style="text-align: center; color: black; font-size: 0.85rem; margin-top: 10px;">Out of {total_sims:,} simulations</p>
        </div>
    </div>

    <!-- Regional Breakdown -->
    <div style="margin-top: 40px;">
        <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.4rem; margin-bottom: 20px;">
            Regional Breakdown - Projected Vote Shares
        </h2>
"""
for region in regions:
    if region not in regional_stats:
        continue
    stats = regional_stats[region]
    stats_html += f"""
        <div style="margin-bottom: 30px;">
            <h3 style="color: black; font-size: 1.1rem; margin-bottom: 10px;">
                {region}
                <span style="font-size: 0.9rem; color: black;">({stats['turnout_pct']:.1f}% of district turnout, {stats['num_precincts']} precincts)</span>
            </h3>
            <table style="width: 100%; max-width: 800px; border-collapse: collapse; font-size: 0.9rem; margin: 0 auto;">
                <thead><tr style="background-color: #f0f0f0;">
                    <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                    <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Projected Vote Share</th>
                </tr></thead><tbody>
"""
    for cand, share in sorted(stats['candidate_shares'].items(), key=lambda x: x[1], reverse=True):
        stats_html += f"""
                <tr><td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                    <td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{share:.1f}%</td></tr>
"""
    stats_html += """        </tbody></table></div>"""

# Most Competitive Precincts
stats_html += """
    </div>
    <div style="margin-top: 40px;">
        <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.4rem; margin-bottom: 20px;">
            Top 10 Most Competitive Precincts
        </h2>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd; min-width: 150px;">Precinct</th>
"""
for cand in CANDIDATES:
    stats_html += f'<th style="padding: 8px; text-align: center; border: 1px solid #ddd;" colspan="2">{cand}</th>\n'
stats_html += """                    </tr>
                    <tr style="background-color: #f8f8f8;">
                        <th style="padding: 6px; border: 1px solid #ddd;"></th>
"""
for _ in CANDIDATES:
    stats_html += """<th style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.75rem;">Win%</th>
                        <th style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.75rem;">Vote%</th>\n"""
stats_html += """                    </tr></thead><tbody>"""

for idx, row in competitive_precincts.iterrows():
    precinct_name = row.get('precinct_name', row.get('JoinField_csv', row.get('JoinField_shape', 'Unknown')))
    sorted_probs = get_sorted_probabilities(row)
    stats_html += f'<tr><td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold;">{precinct_name}</td>\n'
    for cand in CANDIDATES:
        win_prob = row[f'win_prob_{cand}'] * 100
        vote_pct = row[f'median_pct_{cand}']
        bg = ("background-color: #90EE90;" if cand == sorted_probs[0][0]
              else "background-color: #FFE4B5;" if cand == sorted_probs[1][0]
              else "")
        stats_html += (f'<td style="padding: 6px; border: 1px solid #ddd; text-align: center; font-family: monospace; {bg}">{win_prob:.1f}</td>'
                       f'<td style="padding: 6px; border: 1px solid #ddd; text-align: center; font-family: monospace; {bg}">{vote_pct:.1f}</td>\n')
    stats_html += "</tr>\n"

stats_html += """            </tbody></table></div>
        <p style="text-align: center; color: black; font-size: 0.85rem; margin-top: 10px;">
            <span style="background-color: #90EE90; padding: 2px 6px;">Green</span> = Most likely winner |
            <span style="background-color: #FFE4B5; padding: 2px 6px;">Orange</span> = Second most likely
        </p>
    </div>
</div>
"""

# ============================================================================
# BANKED VOTE HTML
# ============================================================================

region_display_names = {
    'Chicago':       'City of Chicago',
    'Suburban Cook': 'Suburban Cook County (incl. Evanston)',
    'Lake County':   'Lake County',
    'McHenry County':'McHenry County',
}

if banked_by_region and district_banked and batch_log:
    total_banked_votes = sum(district_banked.values())
    sorted_cands_banked = sorted(CANDIDATES, key=lambda c: district_banked[c], reverse=True)

    banked_html = f"""
<div style="max-width: 1400px; margin: 40px auto; padding: 20px; font-family: Arial, sans-serif;">
    <h2 style="text-align: center; color: black; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.4rem; margin-bottom: 8px;">
        Estimated Banked Vote by Region
    </h2>
    <p style="text-align: center; color: #555; font-size: 0.9rem; margin-bottom: 8px;">
        Each batch of votes is distributed using the polling baseline from the closest
        historical snapshot ≤ the vote report date, blended with regional vote share
        patterns. Update <code>data/csv_data/votes.csv</code> as new totals come in.
    </p>
"""

    # Batch log table
    banked_html += """
    <div style="margin-bottom: 28px; overflow-x: auto;">
        <h3 style="color: black; font-size: 1.05rem; margin-bottom: 8px; text-align: center;">
            Vote Batch Log — Snapshot Used per Date
        </h3>
        <table style="width: 100%; max-width: 700px; border-collapse: collapse; font-size: 0.85rem; margin: 0 auto;">
            <thead><tr style="background-color: #f0f0f0;">
                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Report Date</th>
                <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">New Votes</th>
                <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Cumulative</th>
                <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Polling Snapshot Used</th>
            </tr></thead><tbody>
"""
    for batch in batch_log:
        banked_html += f"""
            <tr>
                <td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold;">{batch['date']}</td>
                <td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">+{batch['new_votes']:,}</td>
                <td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{batch['cumulative']:,}</td>
                <td style="padding: 6px 8px; border: 1px solid #ddd; font-family: monospace;">{batch['snapshot_used']}</td>
            </tr>
"""
    banked_html += "        </tbody></table></div>\n"

    # Per-region tables
    banked_html += """    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 24px; margin-bottom: 40px;">\n"""

    for region_key in ['Chicago', 'Suburban Cook', 'Lake County', 'McHenry County']:
        rdata = regional_forecast_data.get(region_key, {})
        display_name = region_display_names.get(region_key, region_key)
        region_info = banked_by_region.get(region_key, {})
        cast = region_info.get('cast', 0)
        cand_banked = region_info.get('by_candidate', {})
        expected_turnout = rdata.get('expected_turnout', 0)
        pct_of_expected = (cast / expected_turnout * 100) if expected_turnout > 0 else 0
        sorted_regional = sorted(CANDIDATES, key=lambda c: cand_banked.get(c, 0), reverse=True)

        banked_html += f"""
        <div style="background-color: #f9f9f9; border-radius: 8px; padding: 16px;">
            <h3 style="color: black; font-size: 1.05rem; text-align: center; margin-bottom: 4px;">{display_name}</h3>
            <p style="text-align: center; color: #555; font-size: 0.85rem; margin-bottom: 12px;">
                {cast:,} votes cast"""
        if expected_turnout > 0:
            banked_html += f" &nbsp;|&nbsp; ~{pct_of_expected:.1f}% of expected turnout ({expected_turnout:,})"
        banked_html += """</p>
            <table style="width: 100%; border-collapse: collapse; font-size: 0.9rem;">
                <thead><tr style="background-color: #e8e8e8;">
                    <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                    <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Est. Votes</th>
                    <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Share</th>
                </tr></thead><tbody>
"""
        for i, cand in enumerate(sorted_regional):
            est_v = cand_banked.get(cand, 0)
            share = (est_v / cast * 100) if cast > 0 else 0
            row_bg = "#ffffff" if i % 2 == 0 else "#f4f4f4"
            cand_color = COLORS.get(cand, '#333')
            banked_html += f"""
                <tr style="background-color: {row_bg};">
                    <td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold;">
                        <span style="display:inline-block; width:10px; height:10px; background:{cand_color}; border-radius:2px; margin-right:5px;"></span>{cand}
                    </td>
                    <td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{est_v:,}</td>
                    <td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{share:.1f}%</td>
                </tr>
"""
        banked_html += "            </tbody></table></div>\n"

    banked_html += "    </div>\n"

    # District-wide rollup
    district_expected_turnout = sum(
        regional_forecast_data.get(r, {}).get('expected_turnout', 0)
        for r in ['Chicago', 'Suburban Cook', 'Lake County', 'McHenry County']
    )
    district_pct_in = (total_banked_votes / district_expected_turnout * 100) if district_expected_turnout > 0 else 0

    banked_html += f"""
    <div style="padding: 20px; background-color: #f0f0f0; border-radius: 8px;">
        <h3 style="text-align: center; color: black; font-size: 1.15rem; margin-bottom: 16px; border-bottom: 2px solid #ccc; padding-bottom: 8px;">
            District-Wide Banked Vote Estimate &nbsp;({total_banked_votes:,} total votes cast)
        </h3>
        <table style="width: 100%; max-width: 600px; border-collapse: collapse; font-size: 0.95rem; margin: 0 auto;">
            <thead><tr style="background-color: #ddd;">
                <th style="padding: 10px 8px; text-align: left; border: 1px solid #ccc;">Candidate</th>
                <th style="padding: 10px 8px; text-align: right; border: 1px solid #ccc;">Est. Banked Votes</th>
                <th style="padding: 10px 8px; text-align: right; border: 1px solid #ccc;">Share of Banked</th>
            </tr></thead><tbody>
"""
    for cand in sorted_cands_banked:
        bv = district_banked[cand]
        share_pct = (bv / total_banked_votes * 100) if total_banked_votes > 0 else 0
        cand_color = COLORS.get(cand, '#333')
        banked_html += f"""
            <tr>
                <td style="padding: 8px; border: 1px solid #ccc; font-weight: bold;">
                    <span style="display:inline-block; width:12px; height:12px; background:{cand_color}; border-radius:2px; margin-right:6px;"></span>{cand}
                </td>
                <td style="padding: 8px; border: 1px solid #ccc; text-align: right; font-family: monospace;">{bv:,}</td>
                <td style="padding: 8px; border: 1px solid #ccc; text-align: right; font-family: monospace;">{share_pct:.1f}%</td>
            </tr>
"""
    banked_html += f"""        </tbody></table>
        <p style="text-align: center; color: #777; font-size: 0.8rem; margin-top: 12px;">
            Estimates use the closest historical polling snapshot for each vote batch,
            blended with regional geographic patterns.
            {f'{district_pct_in:.1f}% of expected district turnout reported.' if district_expected_turnout > 0 else ''}
        </p>
    </div>
</div>
"""

else:
    banked_html = """
<div style="max-width: 1400px; margin: 40px auto; padding: 20px; font-family: Arial, sans-serif; text-align: center; color: #888;">
    <p><em>Banked vote section unavailable — add <code>data/csv_data/votes.csv</code> with cumulative regional vote totals.</em></p>
</div>
"""

# ============================================================================
# FULL HTML OUTPUT
# ============================================================================

print(f"\nSaving map to {OUTPUT_HTML}...")
plotly_html = fig.to_html(include_plotlyjs='cdn', div_id='map-div')

full_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.6">
    <title>IL-09 Democratic Primary Prediction Model</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            background-attachment: fixed;
            min-height: 100vh;
        }}
        body::before {{
            content: '';
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background-image: repeating-linear-gradient(45deg, transparent, transparent 35px,
                rgba(255,255,255,.03) 35px, rgba(255,255,255,.03) 70px);
            pointer-events: none; z-index: 0;
        }}
        nav {{
            background-color: rgba(51,51,51,0.95);
            padding: 15px 0;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            position: relative; z-index: 100;
            backdrop-filter: blur(10px);
        }}
        .nav-container {{
            max-width: 1400px; margin: 0 auto; padding: 0 20px;
            display: flex; justify-content: space-between; align-items: center;
        }}
        .nav-title {{ color: white; font-size: 1.5rem; font-weight: bold; }}
        .nav-button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white; padding: 10px 20px; text-decoration: none;
            border-radius: 25px; font-weight: bold;
        }}
        .container {{
            max-width: 1400px; margin: 40px auto; padding: 20px;
            position: relative; z-index: 1;
        }}
        .hero-section {{
            background: rgba(255,255,255,0.95);
            padding: 40px; border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.2);
            backdrop-filter: blur(10px);
        }}
        .hero-section h1 {{
            text-align: center; margin-bottom: 20px;
            border-bottom: 3px solid #667eea; padding-bottom: 10px;
        }}
        #map-div {{ height: 800px; }}
        footer {{
            background-color: rgba(51,51,51,0.95);
            color: white; text-align: center;
            padding: 20px; margin-top: 50px;
        }}
    </style>
</head>
<body>
<nav>
    <div class="nav-container">
        <div class="nav-title">Cole's Election Models</div>
        <a href="index.html" class="nav-button">Home</a>
        <a href="Chicago Mayor.html" class="nav-button">Chicago Mayoral Races</a>
        <a href="chicago_ideology_map.html" class="nav-button">Chicago Ideology Map</a>
    </div>
</nav>
<div class="container">
    <div class="hero-section">
        <h1>IL-09 Democratic Primary Model</h1>
        <div id="map-container">{plotly_html}</div>
    </div>
</div>
{stats_html}
{banked_html}
<footer>Cole's Election Models</footer>
</body>
</html>
"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(full_html)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("MAP CREATION COMPLETE!")
print("=" * 70)
print(f"\nOpen {OUTPUT_HTML} in your browser.")

print(f"\nPrecinct Summary by Winner:")
for cand in CANDIDATES:
    count = (gdf_merged['winner'] == cand).sum()
    if count > 0:
        print(f"  {cand}: {count} precincts ({count/len(gdf_merged)*100:.1f}%)")

if batch_log:
    total_bv = sum(district_banked.values())
    print(f"\nBanked Vote Summary ({total_bv:,} total votes distributed):")
    for cand in sorted_cands_banked:
        bv = district_banked[cand]
        print(f"  {cand:<16}: {bv:,} ({bv/total_bv*100:.1f}%)")
    print(f"\nBatch log ({len(batch_log)} dates processed):")
    for b in batch_log:
        print(f"  {b['date']}: +{b['new_votes']:,} votes → snapshot {b['snapshot_used']}")

print("\nRegional Breakdown:")
for region, stats in regional_stats.items():
    print(f"  {region}: {stats['turnout_pct']:.1f}% of turnout ({stats['num_precincts']} precincts)")