"""
IL-09 Democratic Primary — Demographic Analysis
================================================
For each candidate, runs OLS regression of actual vote share against
demographic predictors (controlling for all others simultaneously).
Also analyses the relationship between turnout and candidate performance.

Requires: pip install statsmodels
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

try:
    import statsmodels.api as sm
    from statsmodels.stats.outliers_influence import variance_inflation_factor
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    print("NOTE: statsmodels not installed. Install with: pip install statsmodels")
    print("      Falling back to scipy correlations only.\n")

# ============================================================================
# CONFIG
# ============================================================================

PRECINCT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'

CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']

ACTUAL_VOTE_COLS = {
    'Fine':        'Laura Fine',
    'Biss':        'Daniel Biss',
    'Abughazaleh': 'Kat Abughazaleh',
    'Simmons':     'Mike Simmons',
    'Amiwala':     'Bushra Amiwala',
    'Andrew':      'Phil Andrew',
    'Huynh':       'Hoan Huynh',
}

# Curated demographic groups — one representative from each correlated cluster
# to avoid multicollinearity. Full collinear sets are collapsed to a summary var.
DEMO_GROUPS = {
    'Race / Ethnicity': [
        'V_20_VAP_White_pct',
        'V_20_VAP_Black_pct',
        'V_20_VAP_Hispanic_pct',
        'V_20_VAP_Asian_pct',
    ],
    'Education': [
        'bach_pct',
    ],
    'Housing': [
        'owner_pct',       # renter_pct = 1 - owner_pct (collinear)
    ],
    'Commute': [
        'transit_pct',
        'drive_pct',
        'walk_pct',
        'wfh_pct',
    ],
    'Language (non-English)': [
        'Spanish',
        'Polish',
        'Chinese',
        'Korean',
        'Russian',
        'Arabic',
    ],
    'Age (summary)': [
        # Use median_voting_age as scalar rather than all 9 correlated brackets
        'median_voting_age',
    ],
    'Income (summary)': [
        'median_household_income',
    ],
    'Ideology': [
        'prog_score_imputed',
    ],
    'LGBT': [
        'lgbt_pct',
    ],
    'Union': [
        'tot_union',
    ],
}

# Flat list of all predictors
ALL_PREDICTORS = [col for cols in DEMO_GROUPS.values() for col in cols]

P_THRESHOLD = 0.05   # significance level
VIF_THRESHOLD = 10   # drop predictors above this VIF

# ============================================================================
# LOAD AND PREPARE DATA
# ============================================================================

print("=" * 70)
print("IL-09 DEMOCRATIC PRIMARY — DEMOGRAPHIC ANALYSIS")
print("=" * 70)

df = pd.read_csv(PRECINCT_CSV)
print(f"\nLoaded {len(df)} precincts")

# Only keep precincts with actual results
for cand, col in ACTUAL_VOTE_COLS.items():
    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

df['Total Votes'] = pd.to_numeric(df['Total Votes'], errors='coerce').fillna(0)
df['Registered Voters'] = pd.to_numeric(df.get('Registered Voters', pd.Series(0)),
                                          errors='coerce').fillna(0)

# Actual vote share per candidate (0-100)
for cand, col in ACTUAL_VOTE_COLS.items():
    df[f'actual_pct_{cand}'] = np.where(
        df['Total Votes'] > 0,
        df[col] / df['Total Votes'] * 100,
        np.nan
    )

# Compute actual winner per precinct from vote counts
vote_count_cols = {f'actual_votes_{c}': c for c in CANDIDATES}
for cand, col in ACTUAL_VOTE_COLS.items():
    df[f'actual_votes_{cand}'] = df[col]

def get_winner(row):
    best_cand, best_votes = None, 0
    for cand in CANDIDATES:
        v = row.get(f'actual_votes_{cand}', 0) or 0
        if v > best_votes:
            best_votes = v
            best_cand = cand
    return best_cand if best_votes > 0 else None

df['actual_winner'] = df.apply(get_winner, axis=1)

# Turnout
df['turnout_pct'] = np.where(
    df['Registered Voters'] > 0,
    df['Total Votes'] / df['Registered Voters'] * 100,
    np.nan
)

# Clean predictors
for col in ALL_PREDICTORS:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    else:
        print(f"  WARNING: predictor '{col}' not found in CSV — skipping")

# Only rows with actual votes reported
df_results = df[df['Total Votes'] > 0].copy()
print(f"Precincts with actual results: {len(df_results)}")

# ── Region dummies (derived from JoinField — reliable, not the misaligned flag cols)
def get_region(jf):
    jf = str(jf).strip().upper()
    if jf.startswith('CITY OF CHICAGO:'): return 'Chicago'
    if jf.startswith('COOK:'):
        n = jf.split(':')[1].strip()
        if n.isdigit() and 7501001 <= int(n) <= 7509999: return 'Evanston'
        return 'Suburban_Cook'
    if jf.startswith('LAKE:'):    return 'Lake_County'
    if jf.startswith('MCHENRY:'): return 'McHenry_County'
    return 'Other'

df_results['region'] = df_results['JoinField'].apply(get_region)
REGIONS       = ['Chicago', 'Evanston', 'Suburban_Cook', 'Lake_County', 'McHenry_County']
REGION_BASE   = 'Suburban_Cook'   # omitted category (reference region)
REGION_DUMMIES = [r for r in REGIONS if r != REGION_BASE]

for r in REGION_DUMMIES:
    df_results[f'reg_{r}'] = (df_results['region'] == r).astype(int)

region_dummy_cols = [f'reg_{r}' for r in REGION_DUMMIES]
print(f"\nRegion distribution:")
for r in REGIONS:
    n = (df_results['region'] == r).sum()
    print(f"  {r:<20}: {n} precincts")

# ============================================================================
# VIF CHECK — remove highly collinear predictors
# ============================================================================

def compute_vifs(df_sub, predictors):
    """Return dict of VIF scores for each predictor."""
    available = [p for p in predictors if p in df_sub.columns
                 and df_sub[p].notna().sum() > 10]
    X = df_sub[available].dropna()
    if len(X) < 10:
        return {p: 0 for p in available}
    X_const = sm.add_constant(X)
    vifs = {}
    for i, col in enumerate(X.columns):
        try:
            vifs[col] = variance_inflation_factor(X_const.values, i + 1)
        except Exception:
            vifs[col] = 999
    return vifs

def filter_by_vif(df_sub, predictors, threshold=VIF_THRESHOLD):
    """Iteratively drop the highest-VIF predictor until all are below threshold."""
    remaining = [p for p in predictors if p in df_sub.columns]
    while True:
        vifs = compute_vifs(df_sub, remaining)
        max_col = max(vifs, key=vifs.get) if vifs else None
        if not max_col or vifs[max_col] <= threshold:
            break
        remaining.remove(max_col)
    return remaining

# ============================================================================
# HELPER: pretty coefficient table
# ============================================================================

def print_coef_table(results, predictors, cand, n):
    """Print significant coefficients sorted by magnitude."""
    rows = []
    for pred in predictors:
        if pred not in results.params:
            continue
        coef  = results.params[pred]
        pval  = results.pvalues[pred]
        ci_lo = results.conf_int().loc[pred, 0]
        ci_hi = results.conf_int().loc[pred, 1]
        rows.append((pred, coef, pval, ci_lo, ci_hi))

    rows.sort(key=lambda x: abs(x[1]), reverse=True)
    sig   = [(p, c, pv, lo, hi) for p, c, pv, lo, hi in rows if pv < P_THRESHOLD]
    insig = [(p, c, pv, lo, hi) for p, c, pv, lo, hi in rows if pv >= P_THRESHOLD]

    r2  = results.rsquared
    adj = results.rsquared_adj

    print(f"\n  R² = {r2:.3f}  |  Adj R² = {adj:.3f}  |  n = {n}")
    print(f"\n  {'Predictor':<35} {'Coef':>8} {'95% CI':>22} {'p':>8}  {'Sig':>4}")
    print(f"  {'-'*80}")

    if sig:
        print(f"  {'--- SIGNIFICANT (p < 0.05) ---'}")
        for pred, coef, pval, lo, hi in sig:
            stars = '***' if pval < 0.001 else '**' if pval < 0.01 else '*'
            dir_arrow = '▲' if coef > 0 else '▼'
            short = pred.replace('V_20_VAP_', '').replace('X_22_2022_', '') \
                        .replace('Household_Income_', 'Inc_').replace('_pct','%') \
                        .replace('Age_Age_','Age_')
            print(f"  {dir_arrow} {short:<33} {coef:>+8.3f}  [{lo:>+7.3f}, {hi:>+7.3f}]  {pval:>8.4f}  {stars:>4}")

    if insig:
        print(f"\n  --- NOT SIGNIFICANT ---")
        for pred, coef, pval, lo, hi in insig:
            short = pred.replace('V_20_VAP_', '').replace('X_22_2022_', '') \
                        .replace('Household_Income_', 'Inc_').replace('_pct','%') \
                        .replace('Age_Age_','Age_')
            print(f"    {short:<35} {coef:>+8.3f}  [{lo:>+7.3f}, {hi:>+7.3f}]  {pval:>8.4f}")

# ============================================================================
# SECTION 1: OLS REGRESSION — each candidate vs demographics
# ============================================================================

print("\n" + "=" * 70)
print("SECTION 1: MULTIVARIATE OLS — VOTE SHARE VS DEMOGRAPHICS")
print("Controls for all predictors simultaneously")
print(f"Significance threshold: p < {P_THRESHOLD}")
print("=" * 70)

# Filter predictors to those available and non-constant
available_preds = [p for p in ALL_PREDICTORS
                   if p in df_results.columns and df_results[p].std() > 0]

if HAS_STATSMODELS:
    # VIF filter once (same predictor set for all candidates for comparability)
    print(f"\nChecking multicollinearity (VIF threshold = {VIF_THRESHOLD})...")
    filtered_preds = filter_by_vif(df_results, available_preds)
    dropped = set(available_preds) - set(filtered_preds)
    if dropped:
        print(f"  Dropped due to high VIF: {sorted(dropped)}")
    print(f"  Using {len(filtered_preds)} predictors")

    for cand in CANDIDATES:
        dep_var = f'actual_pct_{cand}'
        model_df = df_results[[dep_var] + filtered_preds].dropna()
        if len(model_df) < 20:
            print(f"\n{cand}: insufficient data ({len(model_df)} rows)")
            continue

        y = model_df[dep_var]
        X = sm.add_constant(model_df[filtered_preds])
        try:
            model  = sm.OLS(y, X).fit()
            print(f"\n{'─'*70}")
            print(f"  {cand.upper()} — actual vote share (%) regressed on demographics")
            print_coef_table(model, filtered_preds, cand, len(model_df))
        except Exception as e:
            print(f"\n{cand}: regression failed — {e}")

else:
    # Fallback: simple Pearson correlations
    print("\n(Using Pearson correlations — install statsmodels for full OLS)\n")
    for cand in CANDIDATES:
        dep_var = f'actual_pct_{cand}'
        print(f"\n{'─'*70}")
        print(f"  {cand.upper()} — correlations with vote share")
        corrs = []
        for pred in available_preds:
            sub = df_results[[dep_var, pred]].dropna()
            if len(sub) < 10:
                continue
            r, p = stats.pearsonr(sub[pred], sub[dep_var])
            corrs.append((pred, r, p))
        corrs.sort(key=lambda x: abs(x[1]), reverse=True)
        print(f"\n  {'Predictor':<35} {'r':>8} {'p':>10}  Sig")
        print(f"  {'-'*60}")
        for pred, r, p in corrs:
            sig = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else ''
            short = pred.replace('V_20_VAP_','').replace('X_22_2022_','') \
                        .replace('_pct','%').replace('Household_Income_','Inc_')
            print(f"  {short:<35} {r:>+8.3f} {p:>10.4f}  {sig}")

# ============================================================================
# SECTION 2: TURNOUT ANALYSIS
# ============================================================================

print("\n\n" + "=" * 70)
print("SECTION 2: TURNOUT ANALYSIS")
print("Does high/low turnout benefit particular candidates?")
print("=" * 70)

# 2a: Correlation between turnout and each candidate's vote share
print("\n--- 2a: Correlation between precinct turnout and vote share ---\n")
print(f"  {'Candidate':<16} {'r':>8} {'p':>10}  Direction")
print(f"  {'-'*55}")

turnout_corrs = []
for cand in CANDIDATES:
    dep = f'actual_pct_{cand}'
    sub = df_results[['turnout_pct', dep]].dropna()
    if len(sub) < 10:
        continue
    r, p = stats.pearsonr(sub['turnout_pct'], sub[dep])
    turnout_corrs.append((cand, r, p))

turnout_corrs.sort(key=lambda x: x[1], reverse=True)
for cand, r, p in turnout_corrs:
    sig   = '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else '(ns)'
    dirn  = 'benefits from HIGH turnout' if r > 0.1 else \
            'benefits from LOW turnout'  if r < -0.1 else \
            'neutral to turnout'
    print(f"  {cand:<16} {r:>+8.3f} {p:>10.4f}  {sig:>4}  {dirn}")

# 2b: Turnout quintile breakdown
print("\n--- 2b: Vote share by turnout quintile ---\n")
df_results['turnout_quintile'] = pd.qcut(
    df_results['turnout_pct'], q=5,
    labels=['Q1 lowest', 'Q2', 'Q3', 'Q4', 'Q5 highest']
)
q_means = df_results.groupby('turnout_quintile', observed=True)[
    [f'actual_pct_{c}' for c in CANDIDATES]
].mean()
q_means.columns = CANDIDATES
q_ranges = df_results.groupby('turnout_quintile', observed=True)['turnout_pct'].agg(['min','max'])
q_counts = df_results['turnout_quintile'].value_counts().sort_index()

header = f"  {'Quintile':<26}" + "".join(f" {c:>13}" for c in CANDIDATES)
print(header)
print("  " + "─" * (26 + 14 * len(CANDIDATES)))
for qt in q_means.index:
    lo = q_ranges.loc[qt, 'min']
    hi = q_ranges.loc[qt, 'max']
    n  = q_counts[qt]
    label = f"{qt} ({lo:.0f}-{hi:.0f}%, n={n})"
    winner = q_means.loc[qt].idxmax()   # candidate with highest avg pct in this quintile
    row = f"  {label:<26}"
    for cand in CANDIDATES:
        val = q_means.loc[qt, cand]
        marker = '★' if cand == winner else ' '
        row += f" {marker}{val:>11.1f}%"
    print(row)

print(f"\n  ★ = candidate with highest avg vote share in that turnout quintile")

# 2c: OLS — turnout effect controlling for demographics
if HAS_STATSMODELS and len(filtered_preds) > 0:
    print("\n--- 2c: Turnout effect on vote share (controlling for demographics) ---\n")
    print("  Coefficient on turnout_pct after controlling for all demographic predictors\n")
    print(f"  {'Candidate':<16} {'Coef':>8} {'95% CI':>22} {'p':>10}  Interpretation")
    print(f"  {'-'*75}")

    for cand in CANDIDATES:
        dep_var  = f'actual_pct_{cand}'
        preds    = ['turnout_pct'] + filtered_preds
        model_df = df_results[[dep_var] + preds].dropna()
        if len(model_df) < 20:
            continue
        y = model_df[dep_var]
        X = sm.add_constant(model_df[preds])
        try:
            res  = sm.OLS(y, X).fit()
            coef = res.params['turnout_pct']
            pval = res.pvalues['turnout_pct']
            lo   = res.conf_int().loc['turnout_pct', 0]
            hi   = res.conf_int().loc['turnout_pct', 1]
            sig  = '***' if pval < 0.001 else '**' if pval < 0.01 \
                   else '*' if pval < 0.05 else '(ns)'
            interp = f'+{coef:.3f} pp per 1% higher turnout' if coef > 0 \
                     else f'{coef:.3f} pp per 1% higher turnout'
            print(f"  {cand:<16} {coef:>+8.4f}  [{lo:>+7.4f}, {hi:>+7.4f}]  {pval:>10.4f}  {sig}  {interp}")
        except Exception as e:
            print(f"  {cand:<16} regression failed: {e}")

# ============================================================================
# SECTION 3: CANDIDATE CROSS-COMPARISONS — who beat whom where
# ============================================================================

print("\n\n" + "=" * 70)
print("SECTION 3: GEOGRAPHIC / DEMOGRAPHIC PROFILE OF WINNING PRECINCTS")
print("=" * 70)

for cand in CANDIDATES:
    won  = df_results[df_results['actual_winner'] == cand]
    lost = df_results[df_results['actual_winner'] != cand]
    if len(won) < 3:
        continue

    print(f"\n  {cand.upper()} won {len(won)} precincts vs {len(lost)} lost")
    print(f"  {'Demographic':<35} {'Won':>8} {'Lost':>8} {'Diff':>8}  Sig")
    print(f"  {'-'*65}")

    demo_diffs = []
    for pred in available_preds:
        w = won[pred].dropna()
        l = lost[pred].dropna()
        if len(w) < 3 or len(l) < 3:
            continue
        diff = w.mean() - l.mean()
        try:
            _, pval = stats.mannwhitneyu(w, l, alternative='two-sided')
        except Exception:
            pval = 1.0
        demo_diffs.append((pred, w.mean(), l.mean(), diff, pval))

    demo_diffs.sort(key=lambda x: abs(x[3]), reverse=True)
    for pred, wm, lm, diff, pval in demo_diffs[:12]:  # top 12 by magnitude
        sig   = '***' if pval < 0.001 else '**' if pval < 0.01 \
                else '*' if pval < 0.05 else ''
        short = pred.replace('V_20_VAP_','').replace('X_22_2022_','') \
                    .replace('_pct','%').replace('Household_Income_','Inc_') \
                    .replace('Age_Age_','Age_')
        print(f"  {short:<35} {wm:>7.1f}  {lm:>7.1f}  {diff:>+7.1f}  {sig}")

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)

# ============================================================================
# SECTION 4: RANKED CORRELATION MATRIX
# 4a — By candidate: which demographics helped/hurt each candidate most
# 4b — By demographic: which candidates benefitted most/least from each
# ============================================================================

print("\n\n" + "=" * 70)
print("SECTION 4: RANKED CORRELATION MATRIX")
print("Pearson r between demographic and candidate vote share")
print("Positive = demographic associated with higher vote share")
print("=" * 70)

def sig_stars(p):
    if p < 0.001: return '***'
    if p < 0.01:  return '**'
    if p < 0.05:  return '*'
    return '(ns)'

def short_name(pred):
    return (pred.replace('V_20_VAP_', '')
                .replace('X_22_2022_Household_Income_', 'Income_')
                .replace('X_22_2022_Age_Age_', 'Age_')
                .replace('X_22_2022_', '')
                .replace('_pct', '%')
                .replace('prog_score_imputed', 'prog_score')
                .replace('median_voting_age', 'med_age')
                .replace('median_household_income', 'med_income')
                .replace('tot_union', 'union_hh'))

# Build full r/p matrix: corr_matrix[cand][pred] = (r, p)
corr_matrix = {}
for cand in CANDIDATES:
    dep = f'actual_pct_{cand}'
    corr_matrix[cand] = {}
    for pred in available_preds:
        sub = df_results[[dep, pred]].dropna()
        if len(sub) < 10:
            corr_matrix[cand][pred] = (np.nan, np.nan)
            continue
        r, p = stats.pearsonr(sub[pred], sub[dep])
        corr_matrix[cand][pred] = (r, p)

# ── 4a: By candidate ──────────────────────────────────────────────────────
print("\n\n--- 4a: BY CANDIDATE — demographics ranked from most to least beneficial ---")
print("    (rank 1 = strongest positive association with that candidate's vote share)\n")

for cand in CANDIDATES:
    rows = []
    for pred in available_preds:
        r, p = corr_matrix[cand].get(pred, (np.nan, np.nan))
        if np.isnan(r):
            continue
        rows.append((pred, r, p))

    # Sort: most positive r first, most negative last
    rows.sort(key=lambda x: x[1], reverse=True)

    print(f"  {'─'*60}")
    print(f"  {cand.upper()}")
    print(f"  {'Rank':<6} {'Demographic':<30} {'r':>8}  {'Sig'}")
    print(f"  {'─'*60}")
    for rank, (pred, r, p) in enumerate(rows, 1):
        direction = '▲' if r > 0 else '▼'
        stars = sig_stars(p)
        name  = short_name(pred)
        print(f"  {rank:<6} {name:<30} {direction}{r:>+7.3f}  {stars}")
    print()

# ── 4b: By demographic ────────────────────────────────────────────────────
print("\n--- 4b: BY DEMOGRAPHIC — candidates ranked from most to least benefitted ---")
print("    (rank 1 = candidate with strongest positive correlation to this demographic)\n")

for pred in available_preds:
    rows = []
    for cand in CANDIDATES:
        r, p = corr_matrix[cand].get(pred, (np.nan, np.nan))
        if np.isnan(r):
            continue
        rows.append((cand, r, p))

    rows.sort(key=lambda x: x[1], reverse=True)

    name = short_name(pred)
    print(f"  {'─'*55}")
    print(f"  {name.upper()}")
    print(f"  {'Rank':<6} {'Candidate':<16} {'r':>8}  {'Sig'}")
    print(f"  {'─'*55}")
    for rank, (cand, r, p) in enumerate(rows, 1):
        direction = '▲' if r > 0 else '▼'
        stars = sig_stars(p)
        print(f"  {rank:<6} {cand:<16} {direction}{r:>+7.3f}  {stars}")
    print()

print("=" * 70)
print("SECTION 4 COMPLETE")
print("=" * 70)


# ============================================================================
# SECTION 5: GEOGRAPHY-CONTROLLED ANALYSIS
# Re-runs OLS and ranked correlations with region fixed effects added.
# This answers: "Is this demographic effect real, or just a proxy for
# being in Chicago vs Suburban Cook vs McHenry etc?"
#
# Method: include binary region dummies (omitting Suburban Cook as baseline).
# Coefficients on demographics now reflect within-region variation only.
# ============================================================================

print("\n\n" + "=" * 70)
print("SECTION 5: GEOGRAPHY-CONTROLLED ANALYSIS")
print(f"Region fixed effects: {', '.join(REGION_DUMMIES)} (ref: {REGION_BASE})")
print("Coefficients reflect within-region demographic variation")
print("=" * 70)

if not HAS_STATSMODELS:
    print("\n  *** statsmodels required for this section ***")
    print("  Install with: pip install statsmodels")
    print("  Without it we cannot partial out geographic fixed effects.\n")
else:
    # ── 5a: OLS with region fixed effects ──────────────────────────────────
    print("\n--- 5a: OLS WITH REGION FIXED EFFECTS ---")
    print("Comparison: without vs with geography controls\n")

    # VIF on demo preds + region dummies
    all_geo_preds = filtered_preds + region_dummy_cols
    # Region dummies are orthogonal enough that VIF shouldn't be a problem,
    # but re-check anyway
    geo_filtered_preds_demo = filtered_preds  # keep same demo preds as before

    for cand in CANDIDATES:
        dep_var  = f'actual_pct_{cand}'
        all_cols = [dep_var] + geo_filtered_preds_demo + region_dummy_cols
        model_df = df_results[all_cols].dropna()
        if len(model_df) < 20:
            continue

        y = model_df[dep_var]

        # Model A: demographics only (no geography)
        Xa = sm.add_constant(model_df[geo_filtered_preds_demo])
        res_a = sm.OLS(y, Xa).fit()

        # Model B: demographics + region fixed effects
        Xb = sm.add_constant(model_df[geo_filtered_preds_demo + region_dummy_cols])
        res_b = sm.OLS(y, Xb).fit()

        print(f"\n{'─'*70}")
        print(f"  {cand.upper()}")
        print(f"  Without geography: R²={res_a.rsquared:.3f}  |  "
              f"With geography: R²={res_b.rsquared:.3f}  "
              f"(Δ = +{res_b.rsquared - res_a.rsquared:.3f})")

        # Region fixed effects
        print(f"\n  Region fixed effects (vs {REGION_BASE} baseline):")
        for r in REGION_DUMMIES:
            col   = f'reg_{r}'
            coef  = res_b.params.get(col, np.nan)
            pval  = res_b.pvalues.get(col, np.nan)
            stars = sig_stars(pval) if not np.isnan(pval) else ''
            arrow = '▲' if coef > 0 else '▼'
            label = r.replace('_', ' ')
            print(f"    {arrow} {label:<20} {coef:>+7.2f} pp  {stars}")

        # Demographic coefficients — show change vs uncontrolled model
        print(f"\n  Demographic effects (controlled for geography):")
        print(f"  {'Predictor':<30} {'Coef (geo)':>12} {'Coef (no geo)':>14} "
              f"{'Change':>8}  {'p':>8}  Sig")
        print(f"  {'-'*85}")

        rows_geo = []
        for pred in geo_filtered_preds_demo:
            coef_geo  = res_b.params.get(pred, np.nan)
            coef_raw  = res_a.params.get(pred, np.nan)
            pval_geo  = res_b.pvalues.get(pred, np.nan)
            if np.isnan(coef_geo):
                continue
            change = coef_geo - coef_raw if not np.isnan(coef_raw) else np.nan
            rows_geo.append((pred, coef_geo, coef_raw, change, pval_geo))

        rows_geo.sort(key=lambda x: abs(x[1]), reverse=True)

        sig_rows   = [(p, c, cr, ch, pv) for p, c, cr, ch, pv in rows_geo if pv < P_THRESHOLD]
        insig_rows = [(p, c, cr, ch, pv) for p, c, cr, ch, pv in rows_geo if pv >= P_THRESHOLD]

        if sig_rows:
            print(f"  SIGNIFICANT:")
            for pred, coef, coef_raw, change, pval in sig_rows:
                stars = sig_stars(pval)
                arrow = '▲' if coef > 0 else '▼'
                short = pred.replace('V_20_VAP_', '').replace('X_22_2022_', '') \
                            .replace('_pct', '%').replace('Household_Income_', 'Inc_')
                ch_str = f'{change:>+7.3f}' if not np.isnan(change) else '     n/a'
                print(f"  {arrow} {short:<28} {coef:>+12.3f}  {coef_raw:>+14.3f}  "
                      f"{ch_str}  {pval:>8.4f}  {stars}")
        if insig_rows:
            print(f"  NOT SIGNIFICANT:")
            for pred, coef, coef_raw, change, pval in insig_rows:
                short = pred.replace('V_20_VAP_', '').replace('X_22_2022_', '') \
                            .replace('_pct', '%').replace('Household_Income_', 'Inc_')
                ch_str = f'{change:>+7.3f}' if not np.isnan(change) else '     n/a'
                print(f"    {short:<28} {coef:>+12.3f}  {coef_raw:>+14.3f}  "
                      f"{ch_str}  {pval:>8.4f}")

    # ── 5b: Partial correlations controlling for geography ──────────────────
    # Partial r: residualise both Y and X on the region dummies,
    # then correlate the residuals. This is the geography-controlled r.
    print(f"\n\n--- 5b: RANKED PARTIAL CORRELATIONS (controlling for geography) ---")
    print("Compare against raw r from Section 4 — big changes flag geographic confounds\n")

    def partial_r_geo(df_sub, dep, pred):
        """
        Partial correlation of dep ~ pred after removing region fixed effects
        from both variables.
        """
        cols = [dep, pred] + region_dummy_cols
        sub  = df_sub[cols].dropna()
        if len(sub) < 15:
            return np.nan, np.nan

        # Residualise dep on region dummies
        Xr   = sm.add_constant(sub[region_dummy_cols])
        resid_dep  = sm.OLS(sub[dep],  Xr).fit().resid
        resid_pred = sm.OLS(sub[pred], Xr).fit().resid

        r, p = stats.pearsonr(resid_pred, resid_dep)
        return r, p

    # Build partial corr matrix
    partial_matrix = {}
    for cand in CANDIDATES:
        dep = f'actual_pct_{cand}'
        partial_matrix[cand] = {}
        for pred in available_preds:
            r, p = partial_r_geo(df_results, dep, pred)
            partial_matrix[cand][pred] = (r, p)

    # ── 5b-i: By candidate ──────────────────────────────────────────────
    print("  BY CANDIDATE (partial r, geography removed):\n")
    for cand in CANDIDATES:
        rows = []
        for pred in available_preds:
            r_geo, p_geo = partial_matrix[cand].get(pred, (np.nan, np.nan))
            r_raw, _     = corr_matrix[cand].get(pred, (np.nan, np.nan))
            if np.isnan(r_geo):
                continue
            rows.append((pred, r_geo, p_geo, r_raw))

        rows.sort(key=lambda x: x[1], reverse=True)

        print(f"  {'─'*68}")
        print(f"  {cand.upper()}")
        print(f"  {'Rank':<5} {'Demographic':<28} {'Partial r':>10} {'Raw r':>8}  "
              f"{'Δr':>7}  Sig")
        print(f"  {'─'*68}")
        for rank, (pred, r_geo, p_geo, r_raw) in enumerate(rows, 1):
            stars  = sig_stars(p_geo)
            arrow  = '▲' if r_geo > 0 else '▼'
            delta  = r_geo - r_raw if not np.isnan(r_raw) else np.nan
            d_str  = f'{delta:>+6.3f}' if not np.isnan(delta) else '   n/a'
            name   = short_name(pred)
            # Flag large geographic confounding
            flag   = ' ◄ geo confounder' if not np.isnan(delta) and abs(delta) > 0.1 else ''
            print(f"  {rank:<5} {name:<28} {arrow}{r_geo:>+8.3f}  {r_raw:>+7.3f}  "
                  f"{d_str}  {stars}{flag}")
        print()

    # ── 5b-ii: By demographic ────────────────────────────────────────────
    print("\n  BY DEMOGRAPHIC (partial r, geography removed):\n")
    for pred in available_preds:
        rows = []
        for cand in CANDIDATES:
            r_geo, p_geo = partial_matrix[cand].get(pred, (np.nan, np.nan))
            r_raw, _     = corr_matrix[cand].get(pred, (np.nan, np.nan))
            if np.isnan(r_geo):
                continue
            rows.append((cand, r_geo, p_geo, r_raw))

        rows.sort(key=lambda x: x[1], reverse=True)
        name = short_name(pred)

        print(f"  {'─'*60}")
        print(f"  {name.upper()}")
        print(f"  {'Rank':<5} {'Candidate':<16} {'Partial r':>10} {'Raw r':>8}  "
              f"{'Δr':>7}  Sig")
        print(f"  {'─'*60}")
        for rank, (cand, r_geo, p_geo, r_raw) in enumerate(rows, 1):
            stars = sig_stars(p_geo)
            arrow = '▲' if r_geo > 0 else '▼'
            delta = r_geo - r_raw if not np.isnan(r_raw) else np.nan
            d_str = f'{delta:>+6.3f}' if not np.isnan(delta) else '   n/a'
            flag  = ' ◄ geo confounder' if not np.isnan(delta) and abs(delta) > 0.1 else ''
            print(f"  {rank:<5} {cand:<16} {arrow}{r_geo:>+8.3f}  {r_raw:>+7.3f}  "
                  f"{d_str}  {stars}{flag}")
        print()

print("=" * 70)
print("SECTION 5 COMPLETE")
print("=" * 70)


# ============================================================================
# SECTION 6: NOISE DIAGNOSTICS & TURNOUT-WEIGHTED CORRELATIONS
#
# Low base support creates two sources of noise:
#   1. Variance compression — small absolute range of vote shares
#   2. Integer discreteness — small precincts have huge % swings from
#      just 1-2 extra votes
#
# We address this by:
#   a) Showing signal-to-noise diagnostics for each candidate
#   b) Re-running correlations weighted by precinct total votes
#      (larger precincts are more reliable estimates, get more weight)
#   c) A consolidated reliability summary showing which findings survive
#      all three checks: unweighted, weighted, and geography-controlled
# ============================================================================

print("\n\n" + "=" * 70)
print("SECTION 6: NOISE DIAGNOSTICS & TURNOUT-WEIGHTED CORRELATIONS")
print("=" * 70)

# ── 6a: Signal-to-noise diagnostics ─────────────────────────────────────
print("\n--- 6a: SIGNAL-TO-NOISE DIAGNOSTICS BY CANDIDATE ---\n")
print(f"  {'Candidate':<14} {'Mean%':>7} {'Std%':>7} {'Min%':>7} {'Max%':>7} "
      f"{'CV':>7} {'Avg SE':>8}  {'Reliability'}")
print(f"  {'-'*80}")

for cand in CANDIDATES:
    pct_col = f'actual_pct_{cand}'
    pcts = df_results[pct_col].dropna()
    mean_pct = pcts.mean()
    std_pct  = pcts.std()
    min_pct  = pcts.min()
    max_pct  = pcts.max()
    cv       = std_pct / mean_pct if mean_pct > 0 else np.nan
    p        = mean_pct / 100
    avg_n    = df_results['Total Votes'].mean()
    avg_se   = np.sqrt(p * (1 - p) / avg_n) * 100
    noise_var = (df_results.apply(
        lambda row: (row[pct_col] / 100) * (1 - row[pct_col] / 100)
                    / row['Total Votes']
                    if row['Total Votes'] > 0 else np.nan, axis=1
    ) * 10000).mean()
    total_var    = std_pct ** 2
    signal_ratio = max(0, (total_var - noise_var) / total_var) if total_var > 0 else 0
    reliability  = ('HIGH   ' if signal_ratio > 0.7
                    else 'MEDIUM ' if signal_ratio > 0.4
                    else 'LOW  ⚠ ')
    print(f"  {cand:<14} {mean_pct:>6.1f}% {std_pct:>6.2f}% {min_pct:>6.1f}% "
          f"{max_pct:>6.1f}% {cv:>6.2f}x {avg_se:>7.2f}pp  "
          f"{reliability} (signal={signal_ratio:.0%})")

print(f"\n  CV = coefficient of variation (std/mean). Higher = noisier relative to base.")
print(f"  Avg SE = average binomial standard error per precinct (pp).")
print(f"  Signal = fraction of observed variance that is real vs sampling noise.")
print(f"  ⚠ LOW reliability = correlations for this candidate are less trustworthy.")

# ── 6b: Turnout-weighted correlations ────────────────────────────────────
print("\n\n--- 6b: TURNOUT-WEIGHTED CORRELATIONS ---")
print("Weighting precincts by total votes cast (larger precincts are more reliable)")
print("Compare Δr to unweighted — large changes signal noise from small precincts\n")

weights = df_results['Total Votes'].values

def weighted_pearson(x, y, w):
    mask = ~(np.isnan(x) | np.isnan(y) | np.isnan(w)) & (w > 0)
    x, y, w = x[mask], y[mask], w[mask]
    if len(x) < 10:
        return np.nan, np.nan
    w  = w / w.sum()
    mx = np.sum(w * x)
    my = np.sum(w * y)
    cov = np.sum(w * (x - mx) * (y - my))
    sx  = np.sqrt(np.sum(w * (x - mx) ** 2))
    sy  = np.sqrt(np.sum(w * (y - my) ** 2))
    if sx == 0 or sy == 0:
        return np.nan, np.nan
    r   = cov / (sx * sy)
    n_eff = 1 / np.sum(w ** 2)
    t   = r * np.sqrt((n_eff - 2) / (1 - r ** 2)) if abs(r) < 1 else np.inf
    p   = 2 * stats.t.sf(abs(t), df=n_eff - 2)
    return r, p

weighted_matrix = {}
for cand in CANDIDATES:
    dep = df_results[f'actual_pct_{cand}'].values
    weighted_matrix[cand] = {}
    for pred in available_preds:
        x = df_results[pred].values.astype(float)
        r, p = weighted_pearson(x, dep, weights)
        weighted_matrix[cand][pred] = (r, p)

print("  BY CANDIDATE (weighted r vs unweighted r):\n")
for cand in CANDIDATES:
    rows = []
    for pred in available_preds:
        r_w, p_w = weighted_matrix[cand].get(pred, (np.nan, np.nan))
        r_u, _   = corr_matrix[cand].get(pred, (np.nan, np.nan))
        if np.isnan(r_w): continue
        rows.append((pred, r_w, p_w, r_u))
    rows.sort(key=lambda x: x[1], reverse=True)

    print(f"  {'-'*70}")
    print(f"  {cand.upper()}")
    print(f"  {'Rank':<5} {'Demographic':<28} {'Wtd r':>8} {'Raw r':>8} {'Δr':>7}  Sig")
    print(f"  {'-'*70}")
    for rank, (pred, r_w, p_w, r_u) in enumerate(rows, 1):
        stars = sig_stars(p_w)
        arrow = '▲' if r_w > 0 else '▼'
        delta = r_w - r_u if not np.isnan(r_u) else np.nan
        d_str = f'{delta:>+6.3f}' if not np.isnan(delta) else '   n/a'
        flag  = ' ◄ noise' if not np.isnan(delta) and abs(delta) > 0.05 else ''
        name  = short_name(pred)
        print(f"  {rank:<5} {name:<28} {arrow}{r_w:>+6.3f}  {r_u:>+7.3f}  {d_str}  {stars}{flag}")
    print()

print("\n  BY DEMOGRAPHIC (weighted r vs unweighted r):\n")
for pred in available_preds:
    rows = []
    for cand in CANDIDATES:
        r_w, p_w = weighted_matrix[cand].get(pred, (np.nan, np.nan))
        r_u, _   = corr_matrix[cand].get(pred, (np.nan, np.nan))
        if np.isnan(r_w): continue
        rows.append((cand, r_w, p_w, r_u))
    rows.sort(key=lambda x: x[1], reverse=True)
    name = short_name(pred)

    print(f"  {'-'*60}")
    print(f"  {name.upper()}")
    print(f"  {'Rank':<5} {'Candidate':<16} {'Wtd r':>8} {'Raw r':>8} {'Δr':>7}  Sig")
    print(f"  {'-'*60}")
    for rank, (cand, r_w, p_w, r_u) in enumerate(rows, 1):
        stars = sig_stars(p_w)
        arrow = '▲' if r_w > 0 else '▼'
        delta = r_w - r_u if not np.isnan(r_u) else np.nan
        d_str = f'{delta:>+6.3f}' if not np.isnan(delta) else '   n/a'
        flag  = ' ◄ noise' if not np.isnan(delta) and abs(delta) > 0.05 else ''
        print(f"  {rank:<5} {cand:<16} {arrow}{r_w:>+6.3f}  {r_u:>+7.3f}  {d_str}  {stars}{flag}")
    print()

# ── 6c: Combined reliability summary ─────────────────────────────────
print("\n--- 6c: RELIABILITY SUMMARY — which findings to trust most ---\n")
print("  A finding is HIGH confidence if significant in all 3 tests:")
print("  unweighted r (Sec 4) + weighted r (Sec 6b) + geography-controlled (Sec 5)")
print()

for cand in CANDIDATES:
    pct_col = f'actual_pct_{cand}'
    pcts = df_results[pct_col].dropna()
    p_val = pcts.mean() / 100
    avg_n = df_results['Total Votes'].mean()
    noise_var    = p_val * (1 - p_val) / avg_n * 10000
    total_var    = pcts.std() ** 2
    signal_ratio = max(0, (total_var - noise_var) / total_var) if total_var > 0 else 0

    print(f"  {cand.upper()} (signal reliability: {signal_ratio:.0%})")

    high_conf = []
    for pred in available_preds:
        r_u, p_u = corr_matrix[cand].get(pred, (np.nan, np.nan))
        r_w, p_w = weighted_matrix[cand].get(pred, (np.nan, np.nan))
        r_g, p_g = (partial_matrix[cand].get(pred, (np.nan, np.nan))
                    if HAS_STATSMODELS else (np.nan, np.nan))
        sig_u = not np.isnan(p_u) and p_u < P_THRESHOLD
        sig_w = not np.isnan(p_w) and p_w < P_THRESHOLD
        sig_g = not np.isnan(p_g) and p_g < P_THRESHOLD
        n_sig = sum([sig_u, sig_w, sig_g])
        if n_sig >= 2:
            direction = '▲' if r_u > 0 else '▼'
            checks = ('✓unwtd ' if sig_u else '       ') +                      ('✓wtd ' if sig_w else '     ') +                      ('✓geo' if sig_g else '    ')
            confidence = 'HIGH' if n_sig == 3 else 'MEDIUM'
            high_conf.append((short_name(pred), r_u, direction, checks, confidence))

    if high_conf:
        print(f"  {'Demographic':<28} {'r':>7}  {'Checks':<25} Confidence")
        print(f"  {'-'*65}")
        for name, r, direction, checks, confidence in sorted(
                high_conf, key=lambda x: abs(x[1]), reverse=True):
            print(f"  {direction} {name:<26} {r:>+6.3f}  {checks}  {confidence}")
    else:
        print(f"  No findings passed 2+ robustness checks")
    print()

print("=" * 70)
print("SECTION 6 COMPLETE — ALL ANALYSIS DONE")
print("=" * 70)