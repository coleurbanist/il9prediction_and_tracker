"""
IL-09 Democratic Primary — Turnout Map
=======================================
Two layers toggled by a button:
  1. Actual Turnout  — votes cast / registered voters (%)
  2. vs Model        — (actual - expected) / expected * 100 (%)
                       Green = exceeded model, Red = below model

Reads from the same CSV as actual_results_map.py.
Run this script independently; it writes IL09_turnout_map.html.
"""

import geopandas as gpd
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# ============================================================================
# CONFIGURATION  (keep in sync with actual_results_map.py)
# ============================================================================

SHAPEFILE_PATH               = 'data/shapefile/IL24/IL24.shp'
CONGRESSIONAL_DISTRICTS_PATH = 'data/shapefile/congressional_districts.shp'
CHICAGO_BOUNDARY_PATH        = 'data/shapefile/Chicago/Chicago.shp'
EVANSTON_BOUNDARY_PATH       = 'data/shapefile/Evanston/Evanston.shp'
PRECINCT_CSV                 = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
OUTPUT_HTML                  = 'IL09_turnout_map.html'

TOTAL_VOTES_COL  = 'Total Votes'
REG_VOTERS_COL   = 'Registered Voters'
EST_TURNOUT_COL  = 'estimated_turnout'

TURNOUT_MAX          = 65.0    # colorscale ceiling for actual turnout %
TURNOUT_VS_EXP_CAP   = 75.0   # colorscale cap for ±% vs model

# ============================================================================
# STEP 1: LOAD CSV — only the columns we need
# ============================================================================

print("Loading precinct CSV...")
df = pd.read_csv(PRECINCT_CSV)
print(f"  {len(df)} precincts")

# Build reliable display names from JoinField / JoinFieldAlt
def build_display_name(row):
    jf  = str(row.get('JoinField', '') or '').strip()
    alt = str(row.get('JoinFieldAlt', '') or '').strip()
    if jf.upper().startswith('COOK:') and jf.split(':')[1].strip().isdigit():
        if alt and ':' in alt:
            return alt.split(':', 1)[1].strip().title()
        return jf
    if ':' in jf:
        return jf.split(':', 1)[1].strip().title()
    return jf.title()

df['display_name']   = df.apply(build_display_name, axis=1)
df['JoinField_norm'] = df['JoinField'].str.upper()

# Actual votes
df[TOTAL_VOTES_COL] = pd.to_numeric(df.get(TOTAL_VOTES_COL, 0), errors='coerce').fillna(0)
df[REG_VOTERS_COL]  = pd.to_numeric(df.get(REG_VOTERS_COL,  0), errors='coerce').fillna(0)
df[EST_TURNOUT_COL] = pd.to_numeric(df.get(EST_TURNOUT_COL, np.nan), errors='coerce')

# Region from JoinField
def assign_region(jf):
    jf = str(jf).strip().upper()
    if jf.startswith('CITY OF CHICAGO:'): return 'Chicago'
    if jf.startswith('COOK:'):
        suffix = jf.split(':', 1)[1].strip()
        if suffix.isdigit() and 7501001 <= int(suffix) <= 7509999:
            return 'Evanston'
        return 'Suburban Cook'
    if jf.startswith('LAKE:'):    return 'Lake County'
    if jf.startswith('MCHENRY:'): return 'McHenry County'
    return 'Other'

df['region'] = df['JoinField'].apply(assign_region)

print(f"  Columns confirmed: {TOTAL_VOTES_COL}, {REG_VOTERS_COL}, {EST_TURNOUT_COL}")

# ============================================================================
# STEP 2: LOAD SHAPEFILE, CLIP TO IL-09, JOIN
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

# Diagnostic: show what values the district column actually contains
if district_col:
    unique_vals = gdf_congress[district_col].unique().tolist()
    print(f"  District column: '{district_col}'  — sample values: {unique_vals[:10]}")
else:
    print(f"  WARNING: No district column found. Columns: {gdf_congress.columns.tolist()}")

# Broad mask: catches integer 9, string '9', '09', 'IL-09', 'Congressional District 9', etc.
if district_col:
    col_str = gdf_congress[district_col].astype(str).str.strip()
    il09_mask = (
        (col_str == '9') |
        (col_str == '09') |
        (col_str == '9.0') |
        col_str.str.endswith('-9') |
        col_str.str.endswith(' 9') |
        col_str.str.contains(r'\b09\b', regex=True, na=False) |
        col_str.str.contains(r'\b9\b',  regex=True, na=False)
    )
    matched = gdf_congress[il09_mask]
    print(f"  IL-09 mask matched {len(matched)} features")
    if len(matched) == 0:
        print(f"  Falling back to no-clip (using full shapefile extent)")
        il09_geom = None
    else:
        il09_geom = matched.geometry.union_all() \
                    if hasattr(matched.geometry, 'union_all') \
                    else matched.geometry.unary_union
else:
    il09_geom = None

if il09_geom is not None:
    gdf['geometry'] = gdf.geometry.intersection(il09_geom)
    gdf = gdf[~gdf.geometry.is_empty].copy()

print(f"  Clipped to {len(gdf)} precincts in IL-09")

gdf['JoinField_norm'] = gdf['JoinField'].str.upper()
geom_df    = gdf[['JoinField_norm', 'geometry']].copy()
gdf_merged = df.merge(geom_df, on='JoinField_norm', how='inner')

gdf_merged = gpd.GeoDataFrame(gdf_merged, geometry='geometry')
if gdf_merged.crs is None:
    gdf_merged = gdf_merged.set_crs(epsg=4326)
elif gdf_merged.crs.to_epsg() != 4326:
    gdf_merged = gdf_merged.to_crs(epsg=4326)

invalid = ~gdf_merged.geometry.is_valid
if invalid.sum():
    gdf_merged.loc[invalid, 'geometry'] = gdf_merged.loc[invalid, 'geometry'].buffer(0)
gdf_merged = gdf_merged[~gdf_merged.geometry.is_empty].reset_index(drop=True)
print(f"  Joined: {len(gdf_merged)} precincts")

# ============================================================================
# STEP 3: COMPUTE TURNOUT FIELDS
# ============================================================================

gdf_merged[REG_VOTERS_COL]  = pd.to_numeric(gdf_merged.get(REG_VOTERS_COL, 0),  errors='coerce').fillna(0)
gdf_merged[EST_TURNOUT_COL] = pd.to_numeric(gdf_merged.get(EST_TURNOUT_COL, np.nan), errors='coerce')
gdf_merged[TOTAL_VOTES_COL] = pd.to_numeric(gdf_merged.get(TOTAL_VOTES_COL, 0), errors='coerce').fillna(0)

# Actual turnout %
gdf_merged['_turnout_pct'] = np.where(
    gdf_merged[REG_VOTERS_COL] > 0,
    np.clip(gdf_merged[TOTAL_VOTES_COL] / gdf_merged[REG_VOTERS_COL] * 100, 0, TURNOUT_MAX),
    np.nan
)

# vs Expected: (actual - expected) / expected * 100
gdf_merged['_vs_exp_raw'] = np.where(
    gdf_merged[EST_TURNOUT_COL] > 0,
    (gdf_merged[TOTAL_VOTES_COL] - gdf_merged[EST_TURNOUT_COL])
    / gdf_merged[EST_TURNOUT_COL] * 100,
    np.nan
)
gdf_merged['_vs_exp_z'] = np.clip(
    gdf_merged['_vs_exp_raw'], -TURNOUT_VS_EXP_CAP, TURNOUT_VS_EXP_CAP
)

gdf_merged['_t_id']  = range(len(gdf_merged))
gdf_merged['_ve_id'] = range(len(gdf_merged))

# ============================================================================
# STEP 4: HOVER TEXT
# ============================================================================

def hover_turnout(row):
    name      = str(row.get('display_name', '') or '').strip() or 'Unknown'
    region    = row.get('region', '')
    actual    = int(row.get(TOTAL_VOTES_COL, 0) or 0)
    reg       = int(row.get(REG_VOTERS_COL, 0) or 0)
    expected  = row.get(EST_TURNOUT_COL, np.nan)
    exp_str   = f"{int(round(expected)):,}" if not pd.isna(expected) and expected > 0 else 'N/A'

    if reg > 0:
        pct = actual / reg * 100
        return (
            f"<b>{name}</b><br><i>{region}</i><br>"
            f"<span style='font-family:monospace'>"
            f"Votes cast:       {actual:,}<br>"
            f"Registered:       {reg:,}<br>"
            f"Model expected:   {exp_str}<br>"
            f"<b>Turnout: {pct:.1f}%</b>"
            f"</span>"
        )
    return f"<b>{name}</b><br><i>{region}</i><br>No registration data"

def hover_vs_exp(row):
    name     = str(row.get('display_name', '') or '').strip() or 'Unknown'
    region   = row.get('region', '')
    actual   = int(row.get(TOTAL_VOTES_COL, 0) or 0)
    expected = row.get(EST_TURNOUT_COL, np.nan)
    reg      = int(row.get(REG_VOTERS_COL, 0) or 0)

    if pd.isna(expected) or expected <= 0:
        return (
            f"<b>{name}</b><br><i>{region}</i><br>"
            f"No model turnout estimate available"
        )
    exp_i    = int(round(expected))
    diff     = actual - exp_i
    diff_pct = diff / expected * 100
    arrow    = '\u25b2' if diff >= 0 else '\u25bc'
    clr      = 'rgb(0,160,60)' if diff >= 0 else 'rgb(200,40,40)'
    reg_str  = f"{reg:,}" if reg > 0 else 'N/A'
    turnout_str = (f"{actual/reg*100:.1f}%" if reg > 0 else 'N/A')

    return (
        f"<b>{name}</b><br><i>{region}</i><br>"
        f"<span style='font-family:monospace'>"
        f"Actual votes:     {actual:,}<br>"
        f"Expected (model): {exp_i:,}<br>"
        f"Registered:       {reg_str}<br>"
        f"Actual turnout:   {turnout_str}<br>"
        f"<b><span style='color:{clr}'>"
        f"{arrow} {abs(diff):,} votes  ({arrow}{abs(diff_pct):.1f}% of expected)"
        f"</span></b>"
        f"</span>"
    )

hover_t  = gdf_merged.apply(hover_turnout, axis=1)
hover_ve = gdf_merged.apply(hover_vs_exp,  axis=1)

# ============================================================================
# STEP 5: BUILD PLOTLY FIGURE
# ============================================================================

fig = go.Figure()

# ── Trace 0: Actual turnout % ──────────────────────────────────────────────
turnout_colorscale = [
    [0.0,  'rgb(180,0,0)'],
    [0.15, 'rgb(230,80,80)'],
    [0.35, 'rgb(240,180,100)'],
    [0.55, 'rgb(160,220,120)'],
    [1.0,  'rgb(0,140,50)'],
]

fig.add_trace(go.Choroplethmapbox(
    geojson=gdf_merged.__geo_interface__,
    locations=gdf_merged['_t_id'],
    z=gdf_merged['_turnout_pct'],
    zmin=0, zmax=TURNOUT_MAX,
    colorscale=turnout_colorscale,
    showscale=True,
    colorbar=dict(
        title=dict(text='Turnout %', font=dict(color='white', size=11)),
        tickfont=dict(color='white', size=10),
        tickvals=[0, 15, 30, 45, 60, 65],
        ticktext=['0%', '15%', '30%', '45%', '60%', '65%+'],
        len=0.5, thickness=14, x=1.01,
        bgcolor='rgba(0,0,0,0.4)',
    ),
    marker_line_width=0.4,
    marker_line_color='rgba(255,255,255,0.3)',
    marker_opacity=0.85,
    text=hover_t,
    hovertemplate='%{text}<extra></extra>',
    name='Actual Turnout',
    featureidkey='properties._t_id',
    visible=True,
))

# ── Trace 1: vs Model expected ─────────────────────────────────────────────
vs_exp_colorscale = [
    [0.00, 'rgb(180,0,0)'],
    [0.20, 'rgb(230,80,80)'],
    [0.40, 'rgb(245,180,130)'],
    [0.50, 'rgb(240,240,240)'],
    [0.60, 'rgb(140,210,120)'],
    [0.80, 'rgb(30,170,60)'],
    [1.00, 'rgb(0,100,30)'],
]

fig.add_trace(go.Choroplethmapbox(
    geojson=gdf_merged.__geo_interface__,
    locations=gdf_merged['_ve_id'],
    z=gdf_merged['_vs_exp_z'],
    zmin=-TURNOUT_VS_EXP_CAP, zmax=TURNOUT_VS_EXP_CAP,
    colorscale=vs_exp_colorscale,
    showscale=True,
    colorbar=dict(
        title=dict(text='vs Expected', font=dict(color='white', size=11)),
        tickfont=dict(color='white', size=10),
        tickvals=[-75, -50, -25, 0, 25, 50, 75],
        ticktext=['\u226475%', '-50%', '-25%', '0%', '+25%', '+50%', '\u226575%'],
        len=0.5, thickness=14, x=1.01,
        bgcolor='rgba(0,0,0,0.4)',
    ),
    marker_line_width=0.4,
    marker_line_color='rgba(255,255,255,0.3)',
    marker_opacity=0.85,
    text=hover_ve,
    hovertemplate='%{text}<extra></extra>',
    name='vs Model Expected',
    featureidkey='properties._ve_id',
    visible=False,
))

# ── Boundary outlines ──────────────────────────────────────────────────────
def geom_to_lonlat(geom):
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
    try:
        gdf_b = gpd.read_file(shp_path)
        if gdf_b.crs is None: gdf_b = gdf_b.set_crs(epsg=4326)
        else: gdf_b = gdf_b.to_crs(epsg=4326)
        if filter_col and filter_val is not None:
            gdf_b = gdf_b[gdf_b[filter_col].astype(str).str.contains(
                str(filter_val), case=False, na=False)]
        if len(gdf_b) == 0:
            print(f"  WARNING: no features in {shp_path}"); return
        geom = (gdf_b.geometry.union_all()
                if hasattr(gdf_b.geometry, 'union_all')
                else gdf_b.geometry.unary_union)
        lons, lats = geom_to_lonlat(geom)
        fig.add_trace(go.Scattermapbox(
            lon=lons, lat=lats, mode='lines',
            line=dict(width=width, color=color),
            hoverinfo='skip', showlegend=False, visible=True,
        ))
        print(f"  ✓ Boundary: {label}")
    except Exception as e:
        print(f"  ⚠ Could not load boundary {shp_path}: {e}")

print("\nLoading boundary shapefiles...")
add_boundary(CONGRESSIONAL_DISTRICTS_PATH, color='black', width=3.5,
             filter_col=district_col, filter_val='9', label='IL-09 district')
add_boundary(CHICAGO_BOUNDARY_PATH,  color='black', width=2, label='Chicago')
add_boundary(EVANSTON_BOUNDARY_PATH, color='black', width=2, label='Evanston')

n_data_traces     = 2
n_boundary_traces = len(fig.data) - n_data_traces

def make_vis(show_actual, show_vs_exp):
    vis = [show_actual, show_vs_exp] + [True] * n_boundary_traces
    return vis

# Map center — fall back to known IL-09 centroid if GeoDataFrame is empty
if len(gdf_merged) > 0:
    gdf_proj   = gdf_merged.to_crs(epsg=3857)
    union_geom = (gdf_proj.geometry.union_all()
                  if hasattr(gdf_proj.geometry, 'union_all')
                  else gdf_proj.geometry.unary_union)
    center = gpd.GeoSeries([union_geom.centroid], crs=3857).to_crs(4326)[0]
    map_lat, map_lon = center.y, center.x
else:
    print("  WARNING: gdf_merged is empty — using hardcoded IL-09 center")
    map_lat, map_lon = 42.03, -87.79

# ============================================================================
# STEP 6: LAYOUT
# ============================================================================

fig.update_layout(
    mapbox=dict(
        style='carto-positron',
        zoom=9.5,
        center=dict(lat=map_lat, lon=map_lon),
    ),
    margin={'r': 0, 't': 10, 'l': 0, 'b': 0},
    height=800,
    showlegend=False,
    modebar=dict(orientation='v', bgcolor='rgba(255,255,255,0.7)',
                 color='#333', activecolor='#667eea'),
    updatemenus=[dict(
        type='buttons', direction='right',
        x=0.5, xanchor='center', y=1.08, yanchor='top',
        buttons=[
            dict(
                label='Actual Turnout',
                method='update',
                args=[{'visible': make_vis(True, False)}],
            ),
            dict(
                label='vs Model Expected',
                method='update',
                args=[{'visible': make_vis(False, True)}],
            ),
        ],
        bgcolor='white', bordercolor='#333', font=dict(size=13),
    )],
)

# ============================================================================
# STEP 7: DISTRICT STATS FOR PAGE BODY
# ============================================================================

total_votes      = int(gdf_merged[TOTAL_VOTES_COL].sum())
total_registered = int(gdf_merged[REG_VOTERS_COL].sum())
total_expected   = gdf_merged[EST_TURNOUT_COL].sum()
district_turnout = total_votes / total_registered * 100 if total_registered > 0 else 0
vs_exp_district  = (total_votes - total_expected) / total_expected * 100 \
                    if total_expected > 0 else None

# Over/under by region
region_order = ['Chicago', 'Evanston', 'Suburban Cook', 'Lake County', 'McHenry County']
region_stats = []
for region in region_order:
    rdf = gdf_merged[gdf_merged['region'] == region]
    if len(rdf) == 0: continue
    r_actual   = int(rdf[TOTAL_VOTES_COL].sum())
    r_reg      = int(rdf[REG_VOTERS_COL].sum())
    r_expected = rdf[EST_TURNOUT_COL].sum()
    r_pct      = r_actual / r_reg * 100 if r_reg > 0 else 0
    r_vs_exp   = (r_actual - r_expected) / r_expected * 100 if r_expected > 0 else None
    region_stats.append((region, len(rdf), r_actual, r_reg, r_pct, r_expected, r_vs_exp))

def dark_table(title, headers, rows):
    h = (f'<div style="background:rgba(255,255,255,0.06);border-radius:10px;'
         f'padding:20px;min-width:260px;">'
         f'<h2 style="color:#fff;font-size:1.05rem;font-weight:700;letter-spacing:.5px;'
         f'border-bottom:2px solid rgba(255,255,255,0.15);padding-bottom:10px;'
         f'margin-bottom:14px;text-align:center;">{title}</h2>'
         f'<table style="width:100%;border-collapse:collapse;font-size:0.88rem;">'
         f'<thead><tr style="background:rgba(255,255,255,0.08);">')
    for label, align in headers:
        h += (f'<th style="padding:8px 10px;text-align:{align};color:rgba(255,255,255,0.6);'
              f'font-weight:600;font-size:0.78rem;letter-spacing:.4px;'
              f'text-transform:uppercase;">{label}</th>')
    h += '</tr></thead><tbody>'
    for i, cells in enumerate(rows):
        bg = 'background:rgba(255,255,255,0.04);' if i % 2 == 0 else ''
        h += f'<tr style="{bg}">'
        for j, (cell, align) in enumerate(zip(cells, [a for _, a in headers])):
            style = ('color:#fff;font-weight:600;' if j == 0
                     else 'color:rgba(255,255,255,0.85);font-family:monospace;')
            h += f'<td style="padding:8px 10px;text-align:{align};{style}">{cell}</td>'
        h += '</tr>'
    h += '</tbody></table></div>'
    return h

# Summary cards
vs_exp_str = (f"{vs_exp_district:+.1f}%" if vs_exp_district is not None else 'N/A')
vs_exp_clr = ('color:#4caf50' if (vs_exp_district or 0) >= 0 else 'color:#f44336')

summary_html = f"""
<div style="max-width:1400px;margin:0 auto;padding:30px 20px;
            font-family:'Segoe UI',Arial,sans-serif;color:#fff;">
  <h1 style="text-align:center;font-size:1.6rem;font-weight:700;
             letter-spacing:1px;margin-bottom:30px;color:#fff;
             text-shadow:0 2px 8px rgba(0,0,0,0.4);">
    IL-09 Democratic Primary — Turnout Analysis
  </h1>

  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;
              margin-bottom:30px;text-align:center;">
    <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:20px;">
      <div style="font-size:2rem;font-weight:800;">{total_votes:,}</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;">Total Votes Cast</div>
    </div>
    <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:20px;">
      <div style="font-size:2rem;font-weight:800;">{district_turnout:.1f}%</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;">District Turnout Rate</div>
    </div>
    <div style="background:rgba(255,255,255,0.08);border-radius:10px;padding:20px;">
      <div style="font-size:2rem;font-weight:800;{vs_exp_clr}">{vs_exp_str}</div>
      <div style="color:rgba(255,255,255,0.6);font-size:0.9rem;">vs Model Expected</div>
    </div>
  </div>

  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));
              gap:20px;">
"""

# Regional breakdown table
rows_region = []
for region, n_prec, actual, reg, pct, expected, vs_exp in region_stats:
    exp_str  = f"{int(round(expected)):,}" if expected > 0 else 'N/A'
    ve_str   = (f'<span style="color:{"#4caf50" if (vs_exp or 0)>=0 else "#f44336"}">'
                f'{vs_exp:+.1f}%</span>' if vs_exp is not None else 'N/A')
    rows_region.append([
        f"{region} <span style='font-size:0.75rem;color:rgba(255,255,255,0.4)'>({n_prec}p)</span>",
        f"{actual:,}", f"{pct:.1f}%", exp_str, ve_str
    ])

summary_html += dark_table(
    'Regional Breakdown',
    [('Region','left'),('Votes','right'),('Turnout%','right'),
     ('Expected','right'),('vs Model','right')],
    rows_region
)

# Top / bottom precincts by vs-expected deviation
has_exp = gdf_merged[gdf_merged[EST_TURNOUT_COL] > 0].copy()
has_exp['_vs_exp_pct'] = (
    (has_exp[TOTAL_VOTES_COL] - has_exp[EST_TURNOUT_COL])
    / has_exp[EST_TURNOUT_COL] * 100
)
has_exp['_diff_raw'] = has_exp[TOTAL_VOTES_COL] - has_exp[EST_TURNOUT_COL]

top5    = has_exp.nlargest(5,  '_vs_exp_pct')
bottom5 = has_exp.nsmallest(5, '_vs_exp_pct')

def _prec_rows(subset, color):
    rows = []
    for _, row in subset.iterrows():
        name = str(row.get('display_name', '') or 'Unknown').strip()[:28]
        reg  = row.get('region', '')[:14]
        actual   = int(row[TOTAL_VOTES_COL])
        expected = int(round(row[EST_TURNOUT_COL]))
        diff_r   = int(row['_diff_raw'])
        diff_p   = row['_vs_exp_pct']
        arrow    = '▲' if diff_r >= 0 else '▼'
        rows.append([
            f"<span style='font-size:0.78rem'>{name}</span>",
            f"<span style='font-size:0.78rem;color:rgba(255,255,255,0.5)'>{reg}</span>",
            f"{actual:,}",
            f"{expected:,}",
            f'<span style="color:{color}">{arrow}{abs(diff_r):,} ({diff_p:+.0f}%)</span>',
        ])
    return rows

summary_html += dark_table(
    'Most Above Expected',
    [('Precinct','left'),('Region','left'),('Actual','right'),
     ('Expected','right'),('Difference','right')],
    _prec_rows(top5, '#4caf50')
)

summary_html += dark_table(
    'Most Below Expected',
    [('Precinct','left'),('Region','left'),('Actual','right'),
     ('Expected','right'),('Difference','right')],
    _prec_rows(bottom5, '#f44336')
)

summary_html += "  </div>\n</div>"

# ============================================================================
# STEP 8: ASSEMBLE AND WRITE HTML
# ============================================================================

print(f"\nWriting {OUTPUT_HTML}...")
plotly_html = fig.to_html(
    include_plotlyjs='cdn',
    div_id='turnout-map-div',
    config={
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'toImageButtonOptions': {'format': 'png', 'filename': 'IL09_turnout'},
    }
)

full_html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=0.6">
  <title>IL-09 Democratic Primary — Turnout</title>
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
      flex-wrap: wrap; gap: 8px;
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
    #turnout-map-div {{ height: 800px; }}
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
    <a href="IL09_actual_results_map.html" class="nav-button">Actual Results</a>
  </div>
</nav>
<div class="container">
  <div class="hero">
    <h1>IL-09 Democratic Primary — Turnout Analysis</h1>
    <div id="map-container">{plotly_html}</div>
  </div>
</div>
{summary_html}
<footer>Cole's Election Models &nbsp;·&nbsp; IL-09 Democratic Primary 2026</footer>
</body>
</html>
"""

with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
    f.write(full_html)

print(f"\n{'='*60}")
print("TURNOUT MAP COMPLETE")
print(f"{'='*60}")
print(f"\nOpen {OUTPUT_HTML} in your browser.")
print(f"\nDistrict summary:")
print(f"  Total votes:      {total_votes:,}")
print(f"  Registered:       {total_registered:,}")
print(f"  Turnout:          {district_turnout:.1f}%")
if vs_exp_district is not None:
    arrow = '▲' if vs_exp_district >= 0 else '▼'
    print(f"  vs Model:         {arrow}{abs(vs_exp_district):.1f}%")
print(f"\nBy region:")
for region, n_prec, actual, reg, pct, expected, vs_exp in region_stats:
    ve = f"  vs expected: {vs_exp:+.1f}%" if vs_exp is not None else ""
    print(f"  {region:<18} {pct:.1f}% turnout{ve}")