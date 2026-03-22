"""
IL-09 Democratic Primary — Actual Results Map
Reads precinct-level actual vote totals from IL_09_precinct_probabilities.csv
and produces an interactive HTML map showing:
  1. Actual results (winner per precinct, colored by candidate)
  2. Predicted vs Actual accuracy layer (correct/incorrect prediction overlay)
"""

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ============================================================================
# CONFIGURATION
# ============================================================================

SHAPEFILE_PATH               = 'data/shapefile/IL24/IL24.shp'
CONGRESSIONAL_DISTRICTS_PATH = 'data/shapefile/congressional_districts.shp'
CHICAGO_BOUNDARY_PATH        = 'data/shapefile/Chicago/Chicago.shp'
EVANSTON_BOUNDARY_PATH       = 'data/shapefile/Evanston/Evanston.shp'
PRECINCT_CSV                 = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
OUTPUT_HTML                  = 'IL09_actual_results_map.html'

CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']

COLORS = {
    'Fine':        'green',
    'Abughazaleh': 'orange',
    'Biss':        'purple',
    'Amiwala':     'turquoise',
    'Simmons':     'deeppink',
    'Andrew':      'red',
    'Huynh':       'gray',
    'Other':       '#999999',
}

# Exact CSV column names → model candidate
MODELED_RESULT_COLS = {
    'Daniel Biss':     'Biss',
    'Mike Simmons':    'Simmons',
    'Bushra Amiwala':  'Amiwala',
    'Laura Fine':      'Fine',
    'Phil Andrew':     'Andrew',
    'Kat Abughazaleh': 'Abughazaleh',
    'Hoan Huynh':      'Huynh',
}

# Summed into "Other"
OTHER_RESULT_COLS = [
    'Justin Ford',
    'Patricia A. Brown',
    'Jeff Cohen',
    'Nick Pyati',
    'Sam Polan',
    'Bethany Johnson',
    'Howard Rosenblum',
    'Mark Arnold Fredrickson',
]

TOTAL_VOTES_COL = 'Total Votes'

# ============================================================================
# STEP 1: LOAD CSV AND BUILD DISPLAY NAMES
# ============================================================================

print("Loading precinct CSV...")
df = pd.read_csv(PRECINCT_CSV)
print(f"  {len(df)} precincts, {len(df.columns)} columns")

missing_modeled = [c for c in MODELED_RESULT_COLS if c not in df.columns]
if missing_modeled:
    print(f"  WARNING: Missing modeled result columns: {missing_modeled}")

# Build a reliable display name from JoinField / JoinFieldAlt.
# The precinct_name column in the CSV is misaligned (offset from the data rows)
# so we derive names directly from the join keys instead.
def build_display_name(row):
    jf  = str(row.get('JoinField', '') or '').strip()
    alt = str(row.get('JoinFieldAlt', '') or '').strip()

    # COOK:numeric → use JoinFieldAlt which has the readable name, strip prefix
    if jf.upper().startswith('COOK:') and jf.split(':')[1].strip().isdigit():
        if alt and ':' in alt:
            return alt.split(':', 1)[1].strip().title()
        return jf  # fallback

    # CITY OF CHICAGO:WARD XX PRECINCT YY → "Ward XX Precinct YY"
    if ':' in jf:
        parts = jf.split(':', 1)
        return parts[1].strip().title()

    return jf.title()

df['display_name'] = df.apply(build_display_name, axis=1)
df['JoinField_norm'] = df['JoinField'].str.upper()
print(f"  Sample display names: {df['display_name'].head(3).tolist()}")

# ============================================================================
# STEP 2: COMPUTE ACTUAL VOTES AND WINNER PER PRECINCT
# ============================================================================

all_result_cols = list(MODELED_RESULT_COLS.keys()) + OTHER_RESULT_COLS
for col in all_result_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

for csv_col, cand in MODELED_RESULT_COLS.items():
    df[f'actual_votes_{cand}'] = df[csv_col] if csv_col in df.columns else 0

present_other = [c for c in OTHER_RESULT_COLS if c in df.columns]
df['actual_votes_Other'] = df[present_other].sum(axis=1) if present_other else 0

if TOTAL_VOTES_COL in df.columns:
    df['actual_total_votes'] = pd.to_numeric(
        df[TOTAL_VOTES_COL], errors='coerce').fillna(0)
else:
    df['actual_total_votes'] = (
        df[[f'actual_votes_{c}' for c in CANDIDATES] + ['actual_votes_Other']].sum(axis=1)
    )

for cand in CANDIDATES:
    df[f'actual_pct_{cand}'] = np.where(
        df['actual_total_votes'] > 0,
        df[f'actual_votes_{cand}'] / df['actual_total_votes'] * 100,
        0.0,
    )
df['actual_pct_Other'] = np.where(
    df['actual_total_votes'] > 0,
    df['actual_votes_Other'] / df['actual_total_votes'] * 100,
    0.0,
)

winner_vote_cols = {f'actual_votes_{c}': c for c in CANDIDATES}
winner_vote_cols['actual_votes_Other'] = 'Other'

def get_actual_winner(row):
    best = max(winner_vote_cols.keys(), key=lambda c: row.get(c, 0))
    if row.get(best, 0) == 0:
        return 'Other'
    return winner_vote_cols[best]

df['actual_winner'] = df.apply(get_actual_winner, axis=1)

# District totals — computed early so both stats HTML and district layer can use them
sorted_totals_early = sorted(
    [(c, int(df[f'actual_votes_{c}'].sum())) for c in CANDIDATES], key=lambda x: -x[1]
)
other_total_early = int(df['actual_votes_Other'].sum())
grand_total       = sum(v for _, v in sorted_totals_early) + other_total_early

print(f"\nActual winner distribution:")
for cand, count in df['actual_winner'].value_counts().items():
    print(f"  {cand:<20}: {count} precincts")

total_district_votes = int(df['actual_total_votes'].sum())
print(f"\nDistrict-wide votes:")
for cand in CANDIDATES:
    v   = int(df[f'actual_votes_{cand}'].sum())
    pct = v / total_district_votes * 100 if total_district_votes > 0 else 0
    print(f"  {cand:<20}: {v:>7,}  ({pct:.1f}%)")
other_v = int(df['actual_votes_Other'].sum())
print(f"  {'Other':<20}: {other_v:>7,}  ({other_v/total_district_votes*100:.1f}%)")
print(f"  {'TOTAL':<20}: {total_district_votes:>7,}")

# ============================================================================
# STEP 3: PREDICTED WINNER
# Reads from _simplified.csv which win_probability_precinct.py generates.
# That file has JoinField correctly aligned with win_prob_/median_pct_ columns.
# The main CSV has those columns in a different sort order and cannot be used.
# If the simplified CSV is absent, skip the accuracy layer entirely.
# To regenerate: run win_probability_precinct.py first.
# ============================================================================

SIMPLIFIED_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities_simplified.csv'

has_predictions = False
try:
    df_pred = pd.read_csv(SIMPLIFIED_CSV,
                          usecols=['JoinField'] +
                                  [f'median_pct_{c}' for c in CANDIDATES])

    # Detect fraction vs percentage storage
    sample_max = df_pred[f'median_pct_{CANDIDATES[0]}'].max()
    if sample_max < 2.0:
        for c in CANDIDATES:
            df_pred[f'median_pct_{c}'] *= 100

    df_pred['JoinField_norm'] = df_pred['JoinField'].str.upper()
    df_pred['predicted_winner'] = (
        df_pred[[f'median_pct_{c}' for c in CANDIDATES]]
        .idxmax(axis=1)
        .str.replace('median_pct_', '', regex=False)
    )

    # Rename median_pct cols to predicted_pct so they don't clash with
    # the misaligned median_pct cols already in the main CSV
    rename_map = {f'median_pct_{c}': f'predicted_pct_{c}' for c in CANDIDATES}
    df_pred = df_pred.rename(columns=rename_map)

    merge_cols = ['JoinField_norm', 'predicted_winner'] + \
                 [f'predicted_pct_{c}' for c in CANDIDATES]

    df = df.merge(df_pred[merge_cols], on='JoinField_norm', how='left')
    df['prediction_correct'] = df['predicted_winner'] == df['actual_winner']

    n_matched = df['predicted_winner'].notna().sum()
    overall_acc = df.loc[df['predicted_winner'].notna(), 'prediction_correct'].mean() * 100
    has_predictions = True
    print(f"\nPrediction accuracy: {int(df['prediction_correct'].sum())}/{n_matched} "
          f"precincts ({overall_acc:.1f}%)")

except FileNotFoundError:
    print(f"\n  Skipping prediction accuracy — {SIMPLIFIED_CSV} not found.")
    print(f"  Run win_probability_precinct.py to generate it.")
except KeyError as e:
    print(f"\n  Skipping prediction accuracy — missing column {e} in simplified CSV.")

# ============================================================================
# STEP 4: LOAD SHAPEFILE AND JOIN TO IL-09
# ============================================================================

print("\nLoading shapefiles...")
gdf          = gpd.read_file(SHAPEFILE_PATH)
gdf_congress = gpd.read_file(CONGRESSIONAL_DISTRICTS_PATH)

for g in [gdf, gdf_congress]:
    if g.crs is None:
        g.set_crs(epsg=4326, inplace=True)
if gdf_congress.crs != gdf.crs:
    gdf_congress = gdf_congress.to_crs(gdf.crs)

district_col = next(
    (c for c in ['DISTRICT', 'CD', 'CONG_DIST', 'DIST_NUM', 'NAME', 'NAMELSAD']
     if c in gdf_congress.columns), None
)
il09_mask = (
    (gdf_congress[district_col] == '09') |
    (gdf_congress[district_col] == '9')  |
    (gdf_congress[district_col] == 9)    |
    (gdf_congress[district_col].astype(str).str.contains('09', na=False)) |
    (gdf_congress[district_col].astype(str).str.contains('9', na=False))
)
il09_geom = gdf_congress[il09_mask].geometry.unary_union
gdf['geometry'] = gdf.geometry.intersection(il09_geom)
gdf = gdf[~gdf.geometry.is_empty].copy()
print(f"  Clipped to {len(gdf)} precincts in IL-09")

# Join strategy: pull ONLY geometry from the shapefile, then merge onto the
# full CSV dataframe. This avoids all column naming conflicts entirely since
# the shapefile contributes nothing except geometry and JoinField_norm.
gdf['JoinField_norm'] = gdf['JoinField'].str.upper()
df['JoinField_norm']  = df['JoinField'].str.upper()

# Geometry-only frame — just the key and the shapes
geom_df = gdf[['JoinField_norm', 'geometry']].copy()

# Primary join: CSV is the left frame, geometry joins onto it
gdf_merged = df.merge(geom_df, on='JoinField_norm', how='inner')

# Secondary join via JoinField2 for anything still unmatched
if 'JoinField2' in df.columns:
    df['JoinField2_norm'] = df['JoinField2'].str.upper()
    matched_norms  = set(gdf_merged['JoinField_norm'])
    unmatched_csv  = df[~df['JoinField_norm'].isin(matched_norms)].copy()
    unmatched_geom = geom_df[~geom_df['JoinField_norm'].isin(matched_norms)].copy()
    if len(unmatched_csv) > 0 and len(unmatched_geom) > 0:
        extra = unmatched_csv.merge(
            unmatched_geom.rename(columns={'JoinField_norm': 'JoinField2_norm'}),
            on='JoinField2_norm', how='inner'
        )
        if len(extra) > 0:
            print(f"  Secondary join matched {len(extra)} additional precincts")
            gdf_merged = pd.concat([gdf_merged, extra], ignore_index=True)

gdf_merged = gpd.GeoDataFrame(gdf_merged, geometry='geometry')
if gdf_merged.crs is None:
    gdf_merged = gdf_merged.set_crs(epsg=4326)
elif gdf_merged.crs.to_epsg() != 4326:
    gdf_merged = gdf_merged.to_crs(epsg=4326)

invalid = ~gdf_merged.geometry.is_valid
if invalid.sum() > 0:
    gdf_merged.loc[invalid, 'geometry'] = gdf_merged.loc[invalid, 'geometry'].buffer(0)
gdf_merged = gdf_merged[~gdf_merged.geometry.is_empty]
print(f"  Joined: {len(gdf_merged)} precincts with geometry + results")

# ============================================================================
# STEP 5: REGION LABELS AND BOUNDARY OUTLINES
# ============================================================================

def assign_region_from_joinfield(jf):
    """
    Derive region purely from JoinField — the in_chicago / in_evanston etc.
    flag columns in the CSV are misaligned from the data rows and cannot be
    trusted. JoinField is the join key so it is always correctly aligned.

    Rules (all case-insensitive):
      CITY OF CHICAGO:*          → Chicago
      COOK:75xxxxx (7501001-7509005) → Evanston
      COOK:8xxxxxx / COOK:9xxxxxx    → Suburban Cook
      LAKE:*                     → Lake County
      MCHENRY:*                  → McHenry County
    """
    jf = str(jf).strip().upper()
    if jf.startswith('CITY OF CHICAGO:'):
        return 'Chicago'
    if jf.startswith('COOK:'):
        suffix = jf.split(':', 1)[1].strip()
        if suffix.isdigit():
            n = int(suffix)
            if 7501001 <= n <= 7509999:
                return 'Evanston'
            return 'Suburban Cook'
        return 'Suburban Cook'
    if jf.startswith('LAKE:'):
        return 'Lake County'
    if jf.startswith('MCHENRY:'):
        return 'McHenry County'
    return 'Other'

gdf_merged['region'] = gdf_merged['JoinField'].apply(assign_region_from_joinfield)
print(f"\n  Region distribution:")
for region, count in gdf_merged['region'].value_counts().items():
    print(f"    {region:<20}: {count}")

regions = ['Chicago', 'Evanston', 'Suburban Cook', 'Lake County', 'McHenry County']
regional_boundaries = {}
for region in regions:
    mask = gdf_merged['region'] == region
    if mask.sum() > 0:
        regional_boundaries[region] = gdf_merged[mask].geometry.unary_union

# ============================================================================
# STEP 6: HOVER TEXT
# Use display_name built from JoinField/JoinFieldAlt (reliable, not precinct_name
# which is misaligned in the CSV).
# ============================================================================

def make_hover(row):
    winner   = row.get('actual_winner', 'Unknown')
    total    = int(row.get('actual_total_votes', 0))
    region   = row.get('region', '')

    precinct = str(row.get('display_name', '') or '').strip()
    if not precinct or precinct.lower() in ('nan', 'none', ''):
        precinct = 'Unknown'

    cand_data = []
    for cand in CANDIDATES:
        votes = int(row.get(f'actual_votes_{cand}', 0))
        pct   = row.get(f'actual_pct_{cand}', 0)
        if votes > 0:
            cand_data.append((cand, votes, pct))
    other_v = int(row.get('actual_votes_Other', 0))
    if other_v > 0:
        cand_data.append(('Other', other_v, row.get('actual_pct_Other', 0)))
    cand_data.sort(key=lambda x: -x[1])

    # Winning margin
    margin_votes = margin_pct = None
    if len(cand_data) >= 2:
        margin_votes = cand_data[0][1] - cand_data[1][1]
        margin_pct   = cand_data[0][2] - cand_data[1][2]

    # Turnout
    registered = int(row.get('Registered Voters', 0) or 0)
    turnout_pct = (total / registered * 100) if registered > 0 else None

    lines = [
        f"<b>{precinct}</b><br>",
        f"<i>{region}</i><br>",
        "<span style='font-family:monospace'>",
        "Candidate         Votes    Pct<br>",
        "--------------------------------<br>",
    ]
    for cand, votes, pct in cand_data:
        marker = '★ ' if cand == winner else '  '
        lines.append(f"{marker}{cand:<14} {votes:>5}  {pct:>5.1f}%<br>")
    lines += [
        "--------------------------------<br>",
        f"<b>Total Votes: {total:,}</b><br>",
    ]

    # Margin line
    if margin_votes is not None and winner not in ('Unknown', 'Other'):
        lines.append(
            f"<b>{winner} +{margin_votes:,} votes  (+{margin_pct:.1f}%)</b><br>"
        )

    # Turnout line
    if turnout_pct is not None:
        lines.append(
            f"Turnout: {total:,} / {registered:,} ({turnout_pct:.1f}%)<br>"
        )

    if has_predictions:
        pred    = row.get('predicted_winner', '?')
        correct = row.get('prediction_correct', False)
        symbol  = '✓' if correct else '✗'
        lines.append(f"<b>Model predicted: {pred} {symbol}</b><br>")
    lines.append("</span>")
    return "".join(lines)

gdf_merged['hover_text'] = gdf_merged.apply(make_hover, axis=1)

# ============================================================================
# STEP 7: BUILD PLOTLY MAP
# ============================================================================

print("\nBuilding Plotly map...")
fig = go.Figure()

# Layer 1: Actual results, one trace per winner
all_winners = sorted(gdf_merged['actual_winner'].unique())

for winner in all_winners:
    mask   = gdf_merged['actual_winner'] == winner
    subset = gdf_merged[mask].copy().reset_index(drop=True)
    subset['_id'] = range(len(subset))
    color  = COLORS.get(winner, COLORS['Other'])
    fig.add_trace(go.Choroplethmapbox(
        geojson=subset.__geo_interface__,
        locations=subset['_id'],
        z=[1] * len(subset),
        colorscale=[[0, color], [1, color]],
        showscale=False,
        marker_line_width=0.5,
        marker_line_color='white',
        marker_opacity=0.7,
        text=subset['hover_text'],
        hovertemplate='%{text}<extra></extra>',
        name=winner,                           # clean name, no count clutter
        featureidkey='properties._id',
        visible=True,
    ))

# Layer 2: Predicted vs Actual
if has_predictions:
    for correct_val, label, fill_color in [
        (True,  'Correct ✓',   'rgba(0,180,0,0.6)'),
        (False, 'Incorrect ✗', 'rgba(210,30,30,0.6)'),
    ]:
        mask   = gdf_merged['prediction_correct'] == correct_val
        subset = gdf_merged[mask].copy().reset_index(drop=True)
        subset['_id'] = range(len(subset))
        fig.add_trace(go.Choroplethmapbox(
            geojson=subset.__geo_interface__,
            locations=subset['_id'],
            z=[1] * len(subset),
            colorscale=[[0, fill_color], [1, fill_color]],
            showscale=False,
            marker_line_width=1.5,
            marker_line_color='white',
            marker_opacity=0.65,
            text=subset['hover_text'],
            hovertemplate='%{text}<extra></extra>',
            name=label,
            featureidkey='properties._id',
            visible=False,
        ))

# Layer 3: Over/Under performance — one trace per candidate
# z = actual_pct - predicted_pct (percentage points)
# Diverging colorscale: red (underperformed) → white (on target) → candidate color (overperformed)
# Only built if we have predictions to compare against.

perf_candidate_trace_indices = {}  # cand → trace index in fig.data

if has_predictions:
    # Build per-candidate performance hover text
    def make_perf_hover(row, cand):
        display  = str(row.get('display_name', '') or '').strip() or 'Unknown'
        region   = row.get('region', '')
        actual   = row.get(f'actual_pct_{cand}', 0)
        pred_col = f'predicted_pct_{cand}'
        pred     = row.get(pred_col, None)
        if pred is None:
            return f"<b>{display}</b><br><i>{region}</i><br>No prediction data"
        diff = actual - pred
        arrow = '▲' if diff > 0 else '▼' if diff < 0 else '●'
        color = '#4caf50' if diff > 0 else 'tomato' if diff < 0 else '#aaa'
        return (
            f"<b>{display}</b><br>"
            f"<i>{region}</i><br>"
            f"<span style='font-family:monospace'>"
            f"{cand}<br>"
            f"Actual:    {actual:>6.1f}%<br>"
            f"Predicted: {pred:>6.1f}%<br>"
            f"<span style='color:{color};font-weight:bold;'>"
            f"{arrow} {diff:+.1f} pts</span>"
            f"</span>"
        )

    # predicted_pct_{cand} columns are now on gdf_merged from the step-3 merge
    # Nothing extra needed — just verify they're present
    missing_pred = [c for c in CANDIDATES if f'predicted_pct_{c}' not in gdf_merged.columns]
    if missing_pred:
        print(f"  ⚠ Missing predicted_pct columns for: {missing_pred} — performance layer may be incomplete")

    # Build one trace per candidate
    gdf_all = gdf_merged.copy().reset_index(drop=True)
    gdf_all['_perf_id'] = range(len(gdf_all))

    for cand in CANDIDATES:
        cand_color = COLORS[cand]
        pred_col   = f'predicted_pct_{cand}'
        actual_col = f'actual_pct_{cand}'

        has_data = gdf_all[pred_col].notna() & (gdf_all[actual_col] > 0)
        z_vals = np.where(
            has_data,
            gdf_all[actual_col] - gdf_all[pred_col],
            np.nan
        )

        # Clamp to ±20 pp for colorscale (outliers don't wash out the scale)
        z_display = np.where(has_data, np.clip(z_vals, -20, 20), np.nan)

        # No-data precincts get their own grey trace
        no_data_mask = ~has_data
        if no_data_mask.sum() > 0:
            gdf_nodata = gdf_all[no_data_mask].copy().reset_index(drop=True)
            gdf_nodata['_nd_id'] = range(len(gdf_nodata))
            fig.add_trace(go.Choroplethmapbox(
                geojson=gdf_nodata.__geo_interface__,
                locations=gdf_nodata['_nd_id'],
                z=[0] * len(gdf_nodata),
                colorscale=[[0, 'rgb(180,180,180)'], [1, 'rgb(180,180,180)']],
                showscale=False,
                marker_line_width=0.3,
                marker_line_color='rgba(255,255,255,0.2)',
                marker_opacity=0.5,
                hovertemplate='<b>%{text}</b><br><i>No results reported</i><extra></extra>',
                text=gdf_nodata.apply(lambda r: str(r.get('display_name','') or 'Unknown'), axis=1),
                name=f'{cand} no data',
                featureidkey='properties._nd_id',
                visible=False,
            ))
            # Track this grey trace alongside its candidate's performance trace
            perf_candidate_trace_indices[f'{cand}_nodata'] = len(fig.data) - 1

        # Hover text per precinct
        hover_perf = gdf_all.apply(lambda r: make_perf_hover(r, cand), axis=1)

        # Diverging colorscale: red → white → green
        colorscale = [
            [0.0,  'rgb(180,0,0)'],
            [0.35, 'rgb(240,100,100)'],
            [0.5,  'rgb(220,220,220)'],
            [0.65, 'rgb(80,200,100)'],
            [1.0,  'rgb(0,140,50)'],
        ]

        perf_trace_idx = len(fig.data)
        perf_candidate_trace_indices[cand] = perf_trace_idx

        fig.add_trace(go.Choroplethmapbox(
            geojson=gdf_all.__geo_interface__,
            locations=gdf_all['_perf_id'],
            z=z_display,
            zmin=-20, zmax=20,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=dict(text='pp vs model', font=dict(color='white', size=11)),
                tickfont=dict(color='white', size=10),
                tickvals=[-20, -10, 0, 10, 20],
                ticktext=['-20+', '-10', '0', '+10', '+20'],
                len=0.5, thickness=14,
                x=1.01,
                bgcolor='rgba(0,0,0,0.4)',
            ),
            marker_line_width=0.4,
            marker_line_color='rgba(255,255,255,0.3)',
            marker_opacity=0.85,
            text=hover_perf,
            hovertemplate='%{text}<extra></extra>',
            name=f'{cand} performance',
            featureidkey='properties._perf_id',
            visible=False,
        ))

    n_perf_traces = len(CANDIDATES)
else:
    n_perf_traces = 0

# Layer 4: District comparison — one trace per candidate
# z = actual_pct_in_precinct - district_wide_pct
# Same green/red diverging scale as model performance layer.

dist_candidate_trace_indices = {}  # cand → trace index

# Compute district-wide actual pct for each candidate
district_pcts = {}
total_votes_dist = grand_total if 'grand_total' in dir() else int(df['actual_total_votes'].sum())
for cand in CANDIDATES:
    col = f'actual_votes_{cand}'
    district_pcts[cand] = (
        df[col].sum() / total_votes_dist * 100
        if total_votes_dist > 0 else 0
    )

def make_dist_hover(row, cand):
    display  = str(row.get('display_name', '') or '').strip() or 'Unknown'
    region   = row.get('region', '')
    actual   = row.get(f'actual_pct_{cand}', 0)
    dist_avg = district_pcts[cand]
    diff     = actual - dist_avg
    has_votes = row.get(f'actual_votes_{cand}', 0) > 0 or row.get('actual_total_votes', 0) > 0
    if not has_votes:
        return f"<b>{display}</b><br><i>{region}</i><br>No results reported"
    arrow = '▲' if diff > 0 else '▼' if diff < 0 else '●'
    color = '#4caf50' if diff > 0 else 'tomato' if diff < 0 else '#aaa'
    return (
        f"<b>{display}</b><br>"
        f"<i>{region}</i><br>"
        f"<span style='font-family:monospace'>"
        f"{cand}<br>"
        f"Precinct:  {actual:>6.1f}%<br>"
        f"District:  {dist_avg:>6.1f}%<br>"
        f"<span style='color:{color};font-weight:bold;'>"
        f"{arrow} {diff:+.1f} pts</span>"
        f"</span>"
    )

dist_colorscale = [
    [0.0,  'rgb(180,0,0)'],
    [0.35, 'rgb(240,100,100)'],
    [0.5,  'rgb(220,220,220)'],
    [0.65, 'rgb(80,200,100)'],
    [1.0,  'rgb(0,140,50)'],
]

if 'gdf_all' not in dir():
    gdf_all = gdf_merged.copy().reset_index(drop=True)
    gdf_all['_perf_id'] = range(len(gdf_all))

gdf_all['_dist_id'] = range(len(gdf_all))

for cand in CANDIDATES:
    actual_col = f'actual_pct_{cand}'
    has_data   = gdf_all['actual_total_votes'] > 0

    z_vals    = np.where(has_data, gdf_all[actual_col] - district_pcts[cand], np.nan)
    z_display = np.where(has_data, np.clip(z_vals, -20, 20), np.nan)

    # Grey no-data trace
    no_data_mask = ~has_data
    if no_data_mask.sum() > 0:
        gdf_nd = gdf_all[no_data_mask].copy().reset_index(drop=True)
        gdf_nd['_nd2_id'] = range(len(gdf_nd))
        fig.add_trace(go.Choroplethmapbox(
            geojson=gdf_nd.__geo_interface__,
            locations=gdf_nd['_nd2_id'],
            z=[0] * len(gdf_nd),
            colorscale=[[0, 'rgb(180,180,180)'], [1, 'rgb(180,180,180)']],
            showscale=False,
            marker_line_width=0.3,
            marker_line_color='rgba(255,255,255,0.2)',
            marker_opacity=0.5,
            hovertemplate='<b>%{text}</b><br><i>No results reported</i><extra></extra>',
            text=gdf_nd.apply(lambda r: str(r.get('display_name','') or 'Unknown'), axis=1),
            name=f'{cand} dist nodata',
            featureidkey='properties._nd2_id',
            visible=False,
        ))
        dist_candidate_trace_indices[f'{cand}_nodata'] = len(fig.data) - 1

    hover_dist = gdf_all.apply(lambda r: make_dist_hover(r, cand), axis=1)

    dist_trace_idx = len(fig.data)
    dist_candidate_trace_indices[cand] = dist_trace_idx

    fig.add_trace(go.Choroplethmapbox(
        geojson=gdf_all.__geo_interface__,
        locations=gdf_all['_dist_id'],
        z=z_display,
        zmin=-20, zmax=20,
        colorscale=dist_colorscale,
        showscale=True,
        colorbar=dict(
            title=dict(text='pp vs district', font=dict(color='white', size=11)),
            tickfont=dict(color='white', size=10),
            tickvals=[-20, -10, 0, 10, 20],
            ticktext=['-20+', '-10', '0', '+10', '+20'],
            len=0.5, thickness=14,
            x=1.01,
            bgcolor='rgba(0,0,0,0.4)',
        ),
        marker_line_width=0.4,
        marker_line_color='rgba(255,255,255,0.3)',
        marker_opacity=0.85,
        text=hover_dist,
        hovertemplate='%{text}<extra></extra>',
        name=f'{cand} vs district',
        featureidkey='properties._dist_id',
        visible=False,
    ))

n_dist_traces = len([k for k in dist_candidate_trace_indices])

# Layer 5: Turnout map
# z = actual votes / registered voters * 100
# Colorscale: red (0%) → green (65%+)
# Single trace — no candidate selector needed.

TURNOUT_MAX = 65.0   # colorscale ceiling (actual max is 63%)

turnout_colorscale = [
    [0.0,   'rgb(180,0,0)'],
    [0.15,  'rgb(230,80,80)'],
    [0.35,  'rgb(240,180,100)'],
    [0.55,  'rgb(160,220,120)'],
    [1.0,   'rgb(0,140,50)'],
]

def make_turnout_hover(row):
    display    = str(row.get('display_name', '') or '').strip() or 'Unknown'
    region     = row.get('region', '')
    total      = int(row.get('actual_total_votes', 0) or 0)
    registered = int(row.get('Registered Voters', 0) or 0)
    if registered > 0:
        pct = total / registered * 100
        return (
            f"<b>{display}</b><br>"
            f"<i>{region}</i><br>"
            f"<span style='font-family:monospace'>"
            f"Votes cast:  {total:,}<br>"
            f"Registered:  {registered:,}<br>"
            f"<b>Turnout: {pct:.1f}%</b>"
            f"</span>"
        )
    return f"<b>{display}</b><br><i>{region}</i><br>No registration data"

if 'gdf_all' not in dir():
    gdf_all = gdf_merged.copy().reset_index(drop=True)
gdf_all['_turnout_id'] = range(len(gdf_all))

reg_col = 'Registered Voters'
if reg_col not in gdf_all.columns:
    # try to pull from df via JoinField_norm
    reg_df = df[['JoinField_norm', reg_col]].copy() if reg_col in df.columns else None
    if reg_df is not None:
        gdf_all = gdf_all.merge(reg_df, on='JoinField_norm', how='left')

gdf_all[reg_col] = pd.to_numeric(gdf_all.get(reg_col, pd.Series(0, index=gdf_all.index)),
                                   errors='coerce').fillna(0)
gdf_all['_turnout_pct'] = np.where(
    gdf_all[reg_col] > 0,
    np.clip(gdf_all['actual_total_votes'] / gdf_all[reg_col] * 100, 0, TURNOUT_MAX),
    np.nan
)

hover_turnout = gdf_all.apply(make_turnout_hover, axis=1)

turnout_trace_idx = len(fig.data)
fig.add_trace(go.Choroplethmapbox(
    geojson=gdf_all.__geo_interface__,
    locations=gdf_all['_turnout_id'],
    z=gdf_all['_turnout_pct'],
    zmin=0, zmax=TURNOUT_MAX,
    colorscale=turnout_colorscale,
    showscale=True,
    colorbar=dict(
        title=dict(text='Turnout %', font=dict(color='white', size=11)),
        tickfont=dict(color='white', size=10),
        tickvals=[0, 15, 30, 45, 60, 65],
        ticktext=['0%', '15%', '30%', '45%', '60%', '65%+'],
        len=0.5, thickness=14,
        x=1.01,
        bgcolor='rgba(0,0,0,0.4)',
    ),
    marker_line_width=0.4,
    marker_line_color='rgba(255,255,255,0.3)',
    marker_opacity=0.85,
    text=hover_turnout,
    hovertemplate='%{text}<extra></extra>',
    name='Turnout',
    featureidkey='properties._turnout_id',
    visible=False,
))

def geom_to_lonlat(geom):
    """Polygon/MultiPolygon → lon/lat lists with None pen-lift separators."""
    lons, lats = [], []
    polys = list(geom.geoms) if geom.geom_type == 'MultiPolygon' else [geom]
    for poly in polys:
        xs, ys = poly.exterior.xy
        lons += list(xs) + [None]
        lats += list(ys) + [None]
        for interior in poly.interiors:
            xs, ys = interior.xy
            lons += list(xs) + [None]
            lats += list(ys) + [None]
    return lons, lats

def add_boundary(shp_path, color='black', width=3, filter_col=None,
                 filter_val=None, label='boundary'):
    """Load a shapefile and add its outline as a Scattermapbox trace."""
    try:
        gdf_b = gpd.read_file(shp_path)
        if gdf_b.crs is None:
            gdf_b = gdf_b.set_crs(epsg=4326)
        else:
            gdf_b = gdf_b.to_crs(epsg=4326)
        if filter_col and filter_val is not None:
            gdf_b = gdf_b[gdf_b[filter_col].astype(str).str.contains(
                str(filter_val), case=False, na=False)]
        if len(gdf_b) == 0:
            print(f"  WARNING: no features found in {shp_path} "
                  f"(filter: {filter_col}={filter_val})")
            return
        geom = gdf_b.geometry.unary_union
        lons, lats = geom_to_lonlat(geom)
        fig.add_trace(go.Scattermapbox(
            lon=lons, lat=lats,
            mode='lines',
            line=dict(width=width, color=color),
            hoverinfo='skip',
            showlegend=False,
            visible=True,
        ))
        print(f"  ✓ Boundary: {label}")
    except Exception as e:
        print(f"  ⚠ Could not load boundary {shp_path}: {e}")

print("\nLoading boundary shapefiles...")

# IL-09 congressional district outer boundary
add_boundary(
    CONGRESSIONAL_DISTRICTS_PATH,
    color='black', width=3.5,
    filter_col=district_col, filter_val='9',
    label='IL-09 district'
)

# Chicago city boundary
add_boundary(
    CHICAGO_BOUNDARY_PATH,
    color='black', width=2,
    label='Chicago'
)

# Evanston boundary
add_boundary(
    EVANSTON_BOUNDARY_PATH,
    color='black', width=2,
    label='Evanston'
)

# Map center
gdf_proj = gdf_merged.to_crs(epsg=3857)
center   = gpd.GeoSeries(
    [gdf_proj.geometry.unary_union.centroid], crs=3857
).to_crs(4326)[0]

n_actual_traces   = len(all_winners)
n_accuracy_traces = 2 if has_predictions else 0
n_perf_traces_val = len(perf_candidate_trace_indices)
n_dist_traces_val = len(dist_candidate_trace_indices)
n_turnout_traces  = 1
n_boundary_traces = (len(fig.data) - n_actual_traces - n_accuracy_traces
                     - n_perf_traces_val - n_dist_traces_val - n_turnout_traces)

def make_visibility(show_actual, show_accuracy, perf_cand=None,
                    dist_cand=None, show_turnout=False):
    total = len(fig.data)
    vis = [False] * total
    for i in range(n_actual_traces):
        vis[i] = show_actual
    for i in range(n_actual_traces, n_actual_traces + n_accuracy_traces):
        vis[i] = show_accuracy
    if perf_cand:
        for key in [perf_cand, f'{perf_cand}_nodata']:
            idx = perf_candidate_trace_indices.get(key)
            if idx is not None:
                vis[idx] = True
    if dist_cand:
        for key in [dist_cand, f'{dist_cand}_nodata']:
            idx = dist_candidate_trace_indices.get(key)
            if idx is not None:
                vis[idx] = True
    vis[turnout_trace_idx] = show_turnout
    for i in range(total - n_boundary_traces, total):
        vis[i] = True
    return vis

# ---- Main layer toggle buttons ----
buttons_layer = [
    dict(label='Actual Results',
         method='update',
         args=[{'visible': make_visibility(True, False)},
               {'updatemenus[1].visible': False,
                'updatemenus[2].visible': False}]),
]
if has_predictions:
    buttons_layer.append(dict(
        label='Predicted vs Actual',
        method='update',
        args=[{'visible': make_visibility(False, True)},
              {'updatemenus[1].visible': False,
               'updatemenus[2].visible': False}],
    ))
if n_perf_traces_val > 0:
    first_cand = CANDIDATES[0]
    buttons_layer.append(dict(
        label='vs Model',
        method='update',
        args=[{'visible': make_visibility(False, False, perf_cand=first_cand)},
              {'updatemenus[1].visible': True,
               'updatemenus[2].visible': False,
               'updatemenus[1].active': 0}],
    ))
if n_dist_traces_val > 0:
    first_cand = CANDIDATES[0]
    buttons_layer.append(dict(
        label='vs District Avg',
        method='update',
        args=[{'visible': make_visibility(False, False, dist_cand=first_cand)},
              {'updatemenus[1].visible': False,
               'updatemenus[2].visible': True,
               'updatemenus[2].active': 0}],
    ))
buttons_layer.append(dict(
    label='Turnout',
    method='update',
    args=[{'visible': make_visibility(False, False, show_turnout=True)},
          {'updatemenus[1].visible': False,
           'updatemenus[2].visible': False}],
))

# ---- vs Model candidate dropdown ----
perf_dropdown_buttons = []
for cand in CANDIDATES:
    perf_dropdown_buttons.append(dict(
        label=cand,
        method='update',
        args=[{'visible': make_visibility(False, False, perf_cand=cand)}],
    ))

# ---- vs District candidate dropdown ----
dist_dropdown_buttons = []
for cand in CANDIDATES:
    dist_dropdown_buttons.append(dict(
        label=cand,
        method='update',
        args=[{'visible': make_visibility(False, False, dist_cand=cand)}],
    ))

updatemenus = [
    # [0] Main layer toggle
    dict(
        type='buttons', direction='right',
        x=0.5, xanchor='center', y=1.08, yanchor='top',
        buttons=buttons_layer,
        bgcolor='white', bordercolor='#333', font=dict(size=13),
    ),
    # [1] vs Model candidate selector
    dict(
        type='dropdown',
        x=0.5, xanchor='center', y=1.01, yanchor='top',
        buttons=perf_dropdown_buttons,
        bgcolor='rgba(20,20,40,0.95)',
        bordercolor='rgba(255,255,255,0.3)',
        font=dict(size=13, color='white'),
        visible=False,
    ),
    # [2] vs District candidate selector
    dict(
        type='dropdown',
        x=0.5, xanchor='center', y=1.01, yanchor='top',
        buttons=dist_dropdown_buttons,
        bgcolor='rgba(20,20,40,0.95)',
        bordercolor='rgba(255,255,255,0.3)',
        font=dict(size=13, color='white'),
        visible=False,
    ),
]

fig.update_layout(
    mapbox=dict(
        style='carto-positron',
        zoom=9.5,
        center=dict(lat=center.y, lon=center.x),
    ),
    margin={'r': 0, 't': 10, 'l': 0, 'b': 0},
    title=None,
    height=800,
    showlegend=True,
    legend=dict(title='Actual Winner', yanchor='top', y=0.99,
                xanchor='left', x=0.01, bgcolor='rgba(255,255,255,0.9)'),
    modebar=dict(orientation='v', bgcolor='rgba(255,255,255,0.7)',
                 color='#333', activecolor='#667eea'),
    updatemenus=updatemenus,
)

# ============================================================================
# STEP 8: STATS HTML  — dark theme matching prediction map style
# ============================================================================

sorted_totals = sorted_totals_early
other_total   = other_total_early
precinct_wins = gdf_merged['actual_winner'].value_counts().to_dict()
total_prec    = len(gdf_merged)

if has_predictions:
    accuracy_by_region = (
        gdf_merged.groupby('region')['prediction_correct']
        .agg(['sum', 'count', 'mean'])
        .rename(columns={'sum': 'correct', 'count': 'total', 'mean': 'pct'})
        .sort_values('pct', ascending=False)
    )

# ---- helper: render one dark-styled table ----
def dark_table(title, headers, rows, footer=None):
    """
    headers: list of (label, align)  e.g. [('Candidate','left'),('Votes','right')]
    rows:    list of (color_hex_or_None, list_of_cell_strings)
    """
    h = f"""
    <div style="background:rgba(255,255,255,0.06); border-radius:10px;
                padding:20px; min-width:260px;">
      <h2 style="color:#fff; font-size:1.05rem; font-weight:700; letter-spacing:.5px;
                 border-bottom:2px solid rgba(255,255,255,0.15); padding-bottom:10px;
                 margin-bottom:14px; text-align:center;">{title}</h2>
      <table style="width:100%; border-collapse:collapse; font-size:0.88rem;">
        <thead><tr style="background:rgba(255,255,255,0.08);">"""
    for label, align in headers:
        h += f'<th style="padding:8px 10px; text-align:{align}; color:rgba(255,255,255,0.6); font-weight:600; font-size:0.78rem; letter-spacing:.4px; text-transform:uppercase;">{label}</th>'
    h += "</tr></thead><tbody>"
    for i, (color, cells) in enumerate(rows):
        bg = "background:rgba(255,255,255,0.04);" if i % 2 == 0 else ""
        h += f'<tr style="{bg}">'
        for j, (cell, align) in enumerate(zip(cells, [a for _, a in headers])):
            if j == 0 and color:
                h += f'<td style="padding:8px 10px; text-align:{align}; color:#fff; font-weight:600; border-left:3px solid {color}; padding-left:10px;">{cell}</td>'
            else:
                h += f'<td style="padding:8px 10px; text-align:{align}; color:rgba(255,255,255,0.85); font-family:monospace;">{cell}</td>'
        h += "</tr>"
    if footer:
        h += f'<tr style="background:rgba(255,255,255,0.1);"><td colspan="{len(headers)}" style="padding:8px 10px; color:rgba(255,255,255,0.5); font-size:0.8rem; text-align:center;">{footer}</td></tr>'
    h += "</tbody></table></div>"
    return h

stats_html = """
<div style="max-width:1400px; margin:0 auto; padding:30px 20px;
            font-family:'Segoe UI',Arial,sans-serif; color:#fff;">

  <h1 style="text-align:center; font-size:1.6rem; font-weight:700;
             letter-spacing:1px; margin-bottom:30px; color:#fff;
             text-shadow:0 2px 8px rgba(0,0,0,0.4);">
    IL-09 Democratic Primary — Results
  </h1>
"""

# ---- Top grid: Vote Totals | Precincts Won | Accuracy ----
stats_html += '<div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:20px; margin-bottom:36px;">'

# Vote Totals
rows_vt = []
for cand, votes in sorted_totals:
    pct = votes / grand_total * 100 if grand_total > 0 else 0
    rows_vt.append((COLORS[cand], [cand, f"{votes:,}", f"{pct:.1f}%"]))
if other_total > 0:
    op = other_total / grand_total * 100 if grand_total > 0 else 0
    rows_vt.append(('#888', ['Other', f"{other_total:,}", f"{op:.1f}%"]))
rows_vt.append((None, ['<span style="color:#fff;font-weight:700;">Total</span>',
                        f'<span style="color:#fff;font-weight:700;">{grand_total:,}</span>',
                        '<span style="color:#fff;font-weight:700;">100%</span>']))
stats_html += dark_table(
    'District-Wide Vote Totals',
    [('Candidate','left'),('Votes','right'),('Share','right')],
    rows_vt
)

# Precincts Won
rows_pw = []
for cand, wins in sorted(precinct_wins.items(), key=lambda x: -x[1]):
    pct = wins / total_prec * 100 if total_prec > 0 else 0
    color = COLORS.get(cand, '#888')
    rows_pw.append((color, [cand, f"{wins:,}", f"{pct:.1f}%"]))
stats_html += dark_table(
    'Precincts Won',
    [('Candidate','left'),('Precincts','right'),('Share','right')],
    rows_pw,
    footer=f"{total_prec:,} precincts total"
)

# Prediction Accuracy
if has_predictions:
    n_correct = int(gdf_merged['prediction_correct'].sum())
    n_total   = len(gdf_merged)
    rows_acc = []
    for region, row in accuracy_by_region.iterrows():
        pct_val = row['pct'] * 100
        bar_color = '#4caf50' if pct_val >= 70 else '#ff9800' if pct_val >= 50 else '#f44336'
        rows_acc.append((bar_color, [region, str(int(row['correct'])),
                                      str(int(row['total'])), f"{pct_val:.1f}%"]))
    acc_title = f"Model Accuracy &nbsp;<span style='font-size:1.3rem;font-weight:800;color:#4caf50;'>{overall_acc:.1f}%</span> <span style='font-size:0.75rem;color:rgba(255,255,255,0.5);'>({n_correct}/{n_total})</span>"
    stats_html += dark_table(
        acc_title,
        [('Region','left'),('✓','right'),('Total','right'),('Acc.','right')],
        rows_acc
    )

stats_html += '</div>'  # end top grid

# ---- Regional Breakdown ----
stats_html += """
  <h2 style="text-align:center; font-size:1.2rem; font-weight:700; letter-spacing:.5px;
             color:#fff; border-bottom:2px solid rgba(255,255,255,0.15);
             padding-bottom:12px; margin-bottom:24px;">
    Regional Vote Breakdown — Actual Results
  </h2>
  <div style="display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:20px;">
"""

for region in regions:
    region_df    = gdf_merged[gdf_merged['region'] == region]
    if len(region_df) == 0:
        continue
    region_total = region_df['actual_total_votes'].sum()
    n_prec       = len(region_df)

    cand_region = {}
    for cand in CANDIDATES:
        col = f'actual_votes_{cand}'
        if col in region_df.columns:
            cand_region[cand] = int(region_df[col].sum())
    other_r = int(region_df['actual_votes_Other'].sum()) if 'actual_votes_Other' in region_df.columns else 0
    if other_r > 0:
        cand_region['Other'] = other_r

    rows_r = []
    for cand, votes in sorted(cand_region.items(), key=lambda x: -x[1]):
        pct = votes / region_total * 100 if region_total > 0 else 0
        color = COLORS.get(cand, '#888')
        rows_r.append((color, [cand, f"{votes:,}", f"{pct:.1f}%"]))

    region_title = f"{region} <span style='font-size:0.75rem; font-weight:400; color:rgba(255,255,255,0.45);'>({n_prec} precincts · {int(region_total):,} votes)</span>"
    stats_html += dark_table(
        region_title,
        [('Candidate','left'),('Votes','right'),('Share','right')],
        rows_r
    )

stats_html += "  </div>\n</div>"

# ============================================================================
# STEP 9: ASSEMBLE AND WRITE HTML
# ============================================================================

print(f"\nWriting {OUTPUT_HTML}...")
plotly_html = fig.to_html(
    include_plotlyjs='cdn',
    div_id='results-map-div',
    config={
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'toImageButtonOptions': {'format': 'png', 'filename': 'IL09_results'},
    }
)

full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=0.6">
  <title>IL-09 Democratic Primary — Actual Results</title>
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{
      font-family: Arial, sans-serif;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
      background-attachment: fixed;
      min-height: 100vh;
    }}
    nav {{
      background-color: rgba(20,20,40,0.97);
      padding: 15px 0;
      box-shadow: 0 4px 6px rgba(0,0,0,0.4);
      position: relative; z-index: 100;
    }}
    .nav-container {{
      max-width: 1400px; margin: 0 auto; padding: 0 20px;
      display: flex; justify-content: space-between; align-items: center;
    }}
    .nav-title {{ color: white; font-size: 1.4rem; font-weight: bold; }}
    .nav-button {{
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white; padding: 9px 18px; text-decoration: none;
      border-radius: 20px; font-weight: bold; font-size: 0.9rem;
    }}
    .container {{
      max-width: 1400px; margin: 36px auto; padding: 0 20px;
      position: relative; z-index: 1;
    }}
    .hero {{
      background: rgba(255,255,255,0.97);
      padding: 36px; border-radius: 14px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
    }}
    .hero h1 {{
      text-align: center; margin-bottom: 18px;
      border-bottom: 3px solid #333; padding-bottom: 10px;
      font-size: 1.7rem;
    }}
    #results-map-div {{ height: 800px; }}
    footer {{
      background-color: rgba(20,20,40,0.97);
      color: #ccc; text-align: center;
      padding: 18px; margin-top: 50px; font-size: 0.9rem;
    }}
  </style>
</head>
<body>
<nav>
  <div class="nav-container">
    <div class="nav-title">Cole's Election Models</div>
    <a href="index.html" class="nav-button">Home</a>
    <a href="IL09_precinct_map.html" class="nav-button">Prediction Map</a>
  </div>
</nav>
<div class="container">
  <div class="hero">
    <h1>IL-09 Democratic Primary — Actual Results</h1>
    <div id="map-container">{plotly_html}</div>
  </div>
</div>
{stats_html}
<footer>Cole's Election Models &nbsp;·&nbsp; IL-09 Democratic Primary 2026</footer>
</body>
</html>
"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(full_html)

# ============================================================================
# SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("ACTUAL RESULTS MAP COMPLETE!")
print("=" * 70)
print(f"\nOpen {OUTPUT_HTML} in your browser.\n")

print("District-wide results:")
for cand, votes in sorted_totals:
    pct = votes / grand_total * 100 if grand_total > 0 else 0
    bar = '█' * int(pct / 2)
    print(f"  {cand:<20} {votes:>7,}  {pct:>5.1f}%  {bar}")
if other_total > 0:
    print(f"  {'Other':<20} {other_total:>7,}  {other_total/grand_total*100:>5.1f}%")
print(f"  {'TOTAL':<20} {grand_total:>7,}")

print(f"\nPrecincts won:")
for cand, wins in sorted(precinct_wins.items(), key=lambda x: -x[1]):
    print(f"  {cand:<20} {wins:>4} precincts ({wins/total_prec*100:.1f}%)")

if has_predictions:
    print(f"\nPrediction accuracy: {overall_acc:.1f}% "
          f"({int(gdf_merged['prediction_correct'].sum())}/{len(gdf_merged)} precincts)")
    print("\nBy region:")
    for region, row in accuracy_by_region.iterrows():
        print(f"  {region:<35} {row['pct']*100:.1f}%  "
              f"({int(row['correct'])}/{int(row['total'])})")