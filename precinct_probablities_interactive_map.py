import geopandas as gpd
import pandas as pd
import json
import plotly.graph_objects as go

# ============================================================================
# CONFIGURATION
# ============================================================================

SHAPEFILE_PATH = 'data/shapefile/IL24/IL24.shp'
PRECINCT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
DISTRICT_PROBS_JSON = 'district_win_probabilities.json'
POLL_BASELINE_FILE = 'poll_baseline.json'
OUTPUT_HTML = 'IL09_precinct_map.html'
downloadable_csv= 'data/IL_09Probabilites.csv'

CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']

# Color mapping
COLORS = {
    'Fine': 'green',
    'Abughazaleh': 'orange',
    'Biss': 'purple',
    'Amiwala': 'turquoise',
    'Simmons': 'deeppink',
    'Andrew': 'red',
    'Huynh': 'gray'
}


def sort_candidates_by_prob_then_vote(row):
    """Sort candidates by win probability, tiebreak by projected vote"""
    data = []
    for cand in CANDIDATES:
        data.append({
            "candidate": cand,
            "win_prob": row[f"win_prob_{cand}"],
            "median_pct": row[f"median_pct_{cand}"]
        })

    return sorted(
        data,
        key=lambda x: (x["win_prob"], x["median_pct"]),
        reverse=True
    )


def get_sorted_probabilities(row):
    """
    Returns a list of (candidate, win_prob, median_pct),
    sorted by win probability, then projected vote share.
    """
    ranked = sort_candidates_by_prob_then_vote(row)
    return [(r["candidate"], r["win_prob"], r["median_pct"]) for r in ranked]


def calculate_competitiveness(row):
    """Difference between top two win probabilities (smaller = more competitive)"""
    probs = sorted(
        [row[f'win_prob_{cand}'] for cand in CANDIDATES],
        reverse=True
    )
    return probs[0] - probs[1]


# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading data...")

# Load shapefile
gdf = gpd.read_file(SHAPEFILE_PATH)
print(f"✓ Loaded {len(gdf)} precincts from shapefile")

# Load precinct probabilities
df_probs = pd.read_csv(PRECINCT_CSV)
print(f"✓ Loaded {len(df_probs)} precincts from CSV")

# Load district-wide probabilities
with open(DISTRICT_PROBS_JSON, 'r') as f:
    district_data = json.load(f)
    district_win_probs = district_data['win_probabilities']
    district_median = district_data['median_results']
    district_sim_wins = district_data.get('simulation_wins', {})

print(f"✓ Loaded district-wide probabilities")

# Load baseline poll average
with open(POLL_BASELINE_FILE, 'r') as f:
    poll_data = json.load(f)
    baseline_avg = poll_data['baseline']

print(f"✓ Loaded baseline poll average")

# ============================================================================
# FIX JOINFIELD CASE SENSITIVITY ISSUES
# ============================================================================

print("\nFixing JoinField case sensitivity...")

# Create normalized versions for matching
gdf['JoinField_norm'] = gdf['JoinField'].str.upper()
df_probs['JoinField_norm'] = df_probs['JoinField'].str.upper()

# Also try JoinField2 and JoinFieldAlt
df_probs['JoinField2_norm'] = df_probs['JoinField2'].str.upper()
df_probs['JoinFieldAlt_norm'] = df_probs['JoinFieldAlt'].str.upper()

# ============================================================================
# MULTI-STRATEGY JOIN
# ============================================================================

print("Attempting multi-strategy join...")

# Strategy 1: Direct match on normalized JoinField
gdf_merged = gdf.merge(
    df_probs,
    left_on='JoinField_norm',
    right_on='JoinField_norm',
    how='inner',
    suffixes=('_shape', '_csv')
)
print(f"  Strategy 1 (JoinField normalized): {len(gdf_merged)} matches")

# Strategy 2: For unmatched, try JoinField2
unmatched_shape = gdf[~gdf['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]
unmatched_csv = df_probs[~df_probs['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]

if len(unmatched_shape) > 0 and len(unmatched_csv) > 0:
    merge2 = unmatched_shape.merge(
        unmatched_csv,
        left_on='JoinField_norm',
        right_on='JoinField2_norm',
        how='inner',
        suffixes=('_shape', '_csv')
    )
    print(f"  Strategy 2 (JoinField2 normalized): {len(merge2)} additional matches")
    gdf_merged = pd.concat([gdf_merged, merge2], ignore_index=True)

# Strategy 3: For still unmatched, try JoinFieldAlt
unmatched_shape = gdf[~gdf['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]
unmatched_csv = df_probs[~df_probs['JoinField_norm'].isin(gdf_merged['JoinField_norm'])]

if len(unmatched_shape) > 0 and len(unmatched_csv) > 0:
    merge3 = unmatched_shape.merge(
        unmatched_csv,
        left_on='JoinField_norm',
        right_on='JoinFieldAlt_norm',
        how='inner',
        suffixes=('_shape', '_csv')
    )
    print(f"  Strategy 3 (JoinFieldAlt normalized): {len(merge3)} additional matches")
    gdf_merged = pd.concat([gdf_merged, merge3], ignore_index=True)

print(f"\n✓ Total merged: {len(gdf_merged)} precincts")

# Convert to GeoDataFrame (in case concat broke it)
gdf_merged = gpd.GeoDataFrame(gdf_merged, geometry='geometry')

# Convert to WGS84 (EPSG:4326) for Plotly
if gdf_merged.crs is None:
    print("  WARNING: No CRS detected, assuming EPSG:4326")
    gdf_merged = gdf_merged.set_crs(epsg=4326)
elif gdf_merged.crs != 'EPSG:4326':
    print(f"  Converting from {gdf_merged.crs} to EPSG:4326")
    gdf_merged = gdf_merged.to_crs(epsg=4326)

# Verify geometries are valid
invalid_geoms = ~gdf_merged.geometry.is_valid
if invalid_geoms.sum() > 0:
    print(f"  Fixing {invalid_geoms.sum()} invalid geometries...")
    gdf_merged.loc[invalid_geoms, 'geometry'] = gdf_merged.loc[invalid_geoms, 'geometry'].buffer(0)

# Check for empty geometries
empty_geoms = gdf_merged.geometry.is_empty
if empty_geoms.sum() > 0:
    print(f"  WARNING: {empty_geoms.sum()} empty geometries found and will be dropped")
    gdf_merged = gdf_merged[~empty_geoms]

print(f"\n✓ Final dataset: {len(gdf_merged)} precincts ready for mapping")

# ============================================================================
# DETERMINE WINNER PER PRECINCT
# ============================================================================

print("Calculating precinct winners...")


def get_precinct_winner(row):
    ranked = sort_candidates_by_prob_then_vote(row)
    return ranked[0]["candidate"]


gdf_merged['winner'] = gdf_merged.apply(get_precinct_winner, axis=1)
gdf_merged['winner_color'] = gdf_merged['winner'].map(COLORS)

# Competitiveness = probability split between top two
gdf_merged['competitiveness_margin'] = gdf_merged.apply(
    calculate_competitiveness,
    axis=1
)

gdf_merged['competitiveness_margin'] = gdf_merged.apply(calculate_competitiveness, axis=1)

# ============================================================================
# REGIONAL ANALYSIS
# ============================================================================

print("Calculating regional breakdowns...")


# Define regions
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


# Use df_probs for regional analysis (has all precincts)
df_probs['region'] = df_probs.apply(assign_region, axis=1)

# Add region to merged data as well
gdf_merged['region'] = gdf_merged.apply(assign_region, axis=1)

# Calculate regional statistics
regional_stats = {}
total_turnout = df_probs['estimated_turnout'].sum()

regions = ['Chicago', 'Evanston', 'Suburban Cook (not including Evanston)', 'Lake County', 'McHenry County']

for region in regions:
    region_df = df_probs[df_probs['region'] == region]

    if len(region_df) == 0:
        continue

    region_turnout = region_df['estimated_turnout'].sum()
    turnout_pct = (region_turnout / total_turnout) * 100

    # Calculate weighted average median vote share for each candidate
    candidate_shares = {}
    for cand in CANDIDATES:
        weighted_sum = (region_df[f'median_pct_{cand}'] * region_df['estimated_turnout']).sum()
        candidate_shares[cand] = (weighted_sum / region_turnout) if region_turnout > 0 else 0

    regional_stats[region] = {
        'turnout_pct': turnout_pct,
        'candidate_shares': candidate_shares,
        'num_precincts': len(region_df)
    }

# ============================================================================
# FIND MOST COMPETITIVE PRECINCTS
# ============================================================================

print("Identifying most competitive precincts...")

# Get top 10 most competitive precincts (from merged data with geometries)
competitive_precincts = gdf_merged.nsmallest(10, 'competitiveness_margin')

# ============================================================================
# CREATE HOVER TEXT
# ============================================================================

print("Creating hover text...")


def create_hover_text(row):
    # Determine region
    region = row.get('region', 'Unknown')

    precinct_name = row.get(
        'precinct_name',
        row.get('JoinField_csv', row.get('JoinField_shape', 'Unknown'))
    )

    ranked = sort_candidates_by_prob_then_vote(row)

    lines = [
        f"<b>Region: {region}</b><br>",
        f"<b>Precinct: {precinct_name}</b><br>",
        "<span style='font-family: monospace'>",
        "Candidate        Win%    Vote%<br>",
        "-------------------------------<br>"
    ]

    for r in ranked:
        cand = f"{r['candidate']:<14}"
        winp = f"{r['win_prob'] * 100:>5.1f}%"
        vote = f"{r['median_pct']:>6.1f}%"
        lines.append(f"{cand} {winp}  {vote}<br>")

    lines.append("</span>")

    return "".join(lines)


gdf_merged['hover_text'] = gdf_merged.apply(create_hover_text, axis=1)

# ============================================================================
# CREATE MAP
# ============================================================================

print("Creating interactive map...")

# Create figure
fig = go.Figure()

# Add choropleth for each candidate
for cand in CANDIDATES:
    mask = gdf_merged['winner'] == cand
    if mask.sum() > 0:
        gdf_subset = gdf_merged[mask].copy()
        gdf_subset['id'] = range(len(gdf_subset))

        geojson_subset = gdf_subset.__geo_interface__

        fig.add_trace(go.Choroplethmapbox(
            geojson=geojson_subset,
            locations=gdf_subset['id'],
            z=[1] * len(gdf_subset),
            colorscale=[[0, COLORS[cand]], [1, COLORS[cand]]],
            showscale=False,
            marker_line_width=0.5,
            marker_line_color='white',
            marker_opacity=0.85,  # Add transparency to see streets underneath
            text=gdf_subset['hover_text'],
            hovertemplate='%{text}<extra></extra>',
            name=f'{cand} ({mask.sum()} precincts)',
            featureidkey="properties.id"
        ))

# Use projected CRS for centroid calculation
gdf_projected = gdf_merged.to_crs(epsg=3857)
center_point = gdf_projected.geometry.unary_union.centroid
center_point_wgs84 = gpd.GeoSeries([center_point], crs=3857).to_crs(4326)[0]
center_lat = center_point_wgs84.y
center_lon = center_point_wgs84.x

zoom = 9.5

fig.update_layout(
    mapbox=dict(
        # Try 'open-street-map' as it's the most reliable for free web hosting
        style="open-street-map",
        zoom=zoom,
        center=dict(lat=center_lat, lon=center_lon),
    ),
    margin={"r": 0, "t": 50, "l": 0, "b": 0},  # Tighter margins look better on web
    title={
        'text': 'IL-09 Democratic Primary',
        'x': 0.5,
        'xanchor': 'center',
        'font': {'size': 24}
    },
    height=800,
    showlegend=True,
    legend=dict(
        title="Most Likely Winner",
        yanchor="top",
        y=0.99,
        xanchor="left",
        x=0.01,
        bgcolor="rgba(255,255,255,0.8)"
    )
)

# ============================================================================
# CREATE HTML WITH EMBEDDED STATISTICS
# ============================================================================

print("Creating HTML with embedded statistics...")

# Sort candidates by district-wide win probability
sorted_district = sorted(district_win_probs.items(), key=lambda x: x[1], reverse=True)

# Calculate total simulations
total_sims = sum(district_sim_wins.values()) if district_sim_wins else 100000

# Build HTML statistics tables with responsive design
stats_html = """
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

        <!-- Win Probabilities Table -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                District-Wide Win Probabilities
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                        <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Win Prob.</th>
                    </tr>
                </thead>
                <tbody>
"""

for cand, prob in sorted_district:
    stats_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{prob:.1f}%</td>
                    </tr>
"""

stats_html += """
                </tbody>
            </table>
        </div>

        <!-- Baseline Poll Average Table -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                Weighted Poll Average
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                        <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Poll Avg</th>
                    </tr>
                </thead>
                <tbody>
"""

# Sort baseline by value
sorted_baseline = sorted(baseline_avg.items(), key=lambda x: x[1], reverse=True)
for cand, pct in sorted_baseline:
    if cand in CANDIDATES:  # Only show main candidates
        stats_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{pct:.1f}%</td>
                    </tr>
"""

stats_html += """
                </tbody>
            </table>
        </div>

        <!-- Projected Results Table -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                Projected Results
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                        <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Vote Share</th>
                    </tr>
                </thead>
                <tbody>
"""

for cand, prob in sorted_district:
    median = district_median[cand]
    stats_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{median:.1f}%</td>
                    </tr>
"""

stats_html += """
                </tbody>
            </table>
        </div>

        <!-- Simulations Won Table -->
        <div style="width: 100%; max-width: 400px;">
            <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.2rem;">
                Simulations Won
            </h2>
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 0.9rem;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 10px 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                        <th style="padding: 10px 8px; text-align: right; border: 1px solid #ddd;">Wins</th>
                    </tr>
                </thead>
                <tbody>
"""

# Sort by simulation wins
sorted_sim_wins = sorted(district_sim_wins.items(), key=lambda x: x[1], reverse=True) if district_sim_wins else []

for cand, wins in sorted_sim_wins:
    if cand in CANDIDATES:
        stats_html += f"""
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                        <td style="padding: 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{wins:,}</td>
                    </tr>
"""

stats_html += f"""
                </tbody>
            </table>
            <p style="text-align: center; color: #666; font-size: 0.85rem; margin-top: 10px;">
                Out of {total_sims:,} simulations
            </p>
        </div>
    </div>

    <!-- Regional Breakdown Section -->
    <div style="margin-top: 40px;">
        <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.4rem; margin-bottom: 20px;">
            Regional Breakdown - Projected Vote Shares
        </h2>
"""

# Add regional tables
for region in regions:
    if region not in regional_stats:
        continue

    stats = regional_stats[region]
    turnout_pct = stats['turnout_pct']
    shares = stats['candidate_shares']
    num_precincts = stats['num_precincts']

    # Sort candidates by vote share in this region
    sorted_shares = sorted(shares.items(), key=lambda x: x[1], reverse=True)

    stats_html += f"""
        <div style="margin-bottom: 30px;">
            <h3 style="color: #555; font-size: 1.1rem; margin-bottom: 10px;">
                {region} 
                <span style="font-size: 0.9rem; color: #777;">
                    ({turnout_pct:.1f}% of district turnout, {num_precincts} precincts)
                </span>
            </h3>
            <table style="width: 100%; max-width: 800px; border-collapse: collapse; font-size: 0.9rem; margin: 0 auto;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd;">Candidate</th>
                        <th style="padding: 8px; text-align: right; border: 1px solid #ddd;">Projected Vote Share</th>
                    </tr>
                </thead>
                <tbody>
"""

    for cand, share in sorted_shares:
        stats_html += f"""
                    <tr>
                        <td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold;">{cand}</td>
                        <td style="padding: 6px 8px; border: 1px solid #ddd; text-align: right; font-family: monospace;">{share:.1f}%</td>
                    </tr>
"""

    stats_html += """
                </tbody>
            </table>
        </div>
"""

stats_html += """
    </div>

    <!-- Most Competitive Precincts Section -->
    <div style="margin-top: 40px;">
        <h2 style="text-align: center; color: #333; border-bottom: 3px solid #333; padding-bottom: 10px; font-size: 1.4rem; margin-bottom: 20px;">
            Top 10 Most Competitive Precincts
        </h2>
        <div style="overflow-x: auto;">
            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                <thead>
                    <tr style="background-color: #f0f0f0;">
                        <th style="padding: 8px; text-align: left; border: 1px solid #ddd; min-width: 150px;">Precinct</th>
"""

# Add header for each candidate
for cand in CANDIDATES:
    stats_html += f"""
                        <th style="padding: 8px; text-align: center; border: 1px solid #ddd;" colspan="2">{cand}</th>
"""

stats_html += """
                    </tr>
                    <tr style="background-color: #f8f8f8;">
                        <th style="padding: 6px; border: 1px solid #ddd;"></th>
"""

# Sub-headers for Win% and Vote%
for _ in CANDIDATES:
    stats_html += """
                        <th style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.75rem;">Win%</th>
                        <th style="padding: 6px; text-align: center; border: 1px solid #ddd; font-size: 0.75rem;">Vote%</th>
"""

stats_html += """
                    </tr>
                </thead>
                <tbody>
"""

# Add competitive precinct data
for idx, row in competitive_precincts.iterrows():
    precinct_name = row.get('precinct_name', row.get('JoinField_csv', row.get('JoinField_shape', 'Unknown')))

    # Get candidates sorted by win probability for this precinct
    sorted_probs = get_sorted_probabilities(row)

    stats_html += f"""
                    <tr>
                        <td style="padding: 6px 8px; border: 1px solid #ddd; font-weight: bold;">{precinct_name}</td>
"""

    # Add data for each candidate in original order
    for cand in CANDIDATES:
        win_prob = row[f'win_prob_{cand}'] * 100
        vote_pct = row[f'median_pct_{cand}']

        # Highlight top 2 candidates
        bg_color = ""
        if cand == sorted_probs[0][0]:
            bg_color = "background-color: #90EE90;"  # Light green for winner
        elif cand == sorted_probs[1][0]:
            bg_color = "background-color: #FFE4B5;"  # Light orange for 2nd

        stats_html += f"""
                        <td style="padding: 6px; border: 1px solid #ddd; text-align: center; font-family: monospace; {bg_color}">{win_prob:.1f}</td>
                        <td style="padding: 6px; border: 1px solid #ddd; text-align: center; font-family: monospace; {bg_color}">{vote_pct:.1f}</td>
"""

    stats_html += """
                    </tr>
"""

stats_html += """
                </tbody>
            </table>
        </div>
        <p style="text-align: center; color: #666; font-size: 0.85rem; margin-top: 10px;">
            <span style="background-color: #90EE90; padding: 2px 6px;">Green</span> = Most likely winner | 
            <span style="background-color: #FFE4B5; padding: 2px 6px;">Orange</span> = Second most likely
        </p>
    </div>
</div>
"""

# ============================================================================
# SAVE MAP WITH CUSTOM HTML
# ============================================================================

print(f"\nSaving map to {OUTPUT_HTML}...")

# Get the Plotly HTML
plotly_html = fig.to_html(include_plotlyjs='cdn', div_id='map-div')

# Create full HTML with map + statistics
full_html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=0.6">
    <title>IL-09 Democratic Primary Prediction Model</title>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
        }}
        #map-container {{
            width: 100%;
            background-color: white;
        }}

        /* Mobile-specific adjustments */
        @media (max-width: 768px) {{
            h2 {{
                font-size: 1rem !important;
            }}
            h3 {{
                font-size: 0.9rem !important;
            }}
            table {{
                font-size: 0.75rem !important;
            }}
            th, td {{
                padding: 4px 2px !important;
            }}
        }}
    </style>
</head>
<body>
    <div id="map-container">
        {plotly_html}
    </div>
    {stats_html}
</body>
</html>
"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(full_html)

# Print summary statistics
print("\n" + "=" * 70)
print("MAP CREATION COMPLETE!")
print("=" * 70)
print(f"\nOpen {OUTPUT_HTML} in your browser to view the interactive map.")
print(f"\nPrecinct Summary by Winner:")
for cand in CANDIDATES:
    count = (gdf_merged['winner'] == cand).sum()
    if count > 0:
        print(f"  {cand}: {count} precincts ({count / len(gdf_merged) * 100:.1f}%)")

# Check coverage by geography
if 'in_chicago' in gdf_merged.columns:
    chicago_count = gdf_merged['in_chicago'].sum()
    print(f"\nGeographic Coverage:")
    print(f"  Chicago precincts: {int(chicago_count)}")
    if 'in_evanston' in gdf_merged.columns:
        evanston_count = gdf_merged['in_evanston'].sum()
        print(f"  Evanston precincts: {int(evanston_count)}")
    if 'in_cook' in gdf_merged.columns:
        cook_count = gdf_merged['in_cook'].sum()
        print(f"  Cook County precincts: {int(cook_count)}")
    if 'in_lake' in gdf_merged.columns:
        lake_count = gdf_merged['in_lake'].sum()
        print(f"  Lake County precincts: {int(lake_count)}")

print("\nRegional Breakdown:")
for region, stats in regional_stats.items():
    print(f"  {region}: {stats['turnout_pct']:.1f}% of turnout ({stats['num_precincts']} precincts)")