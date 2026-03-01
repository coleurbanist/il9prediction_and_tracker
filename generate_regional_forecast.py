import pandas as pd
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

PRECINCT_CSV = 'data/csv_data/expectations/IL_09_precinct_probabilities.csv'
OUTPUT_JSON = 'regional_vote_forecast.json'

CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']

# ============================================================================
# LOAD DATA
# ============================================================================

print("Loading precinct data...")
df = pd.read_csv(PRECINCT_CSV)
print(f"✓ Loaded {len(df)} precincts")

# ============================================================================
# ASSIGN REGIONS
# NOTE:
#   - "Chicago" = in_chicago == 1
#   - "Suburban Cook" = in_cook == 1 AND in_chicago == 0
#     (this includes Evanston since Evanston is in Cook County)
#   - "Lake County" = in_lake == 1
#   - "McHenry County" = in_mchenry == 1
# ============================================================================

def assign_banked_region(row):
    if row.get('in_chicago', 0) == 1:
        return 'Chicago'
    elif row.get('in_cook', 0) == 1:
        return 'Suburban Cook'   # includes Evanston
    elif row.get('in_lake', 0) == 1:
        return 'Lake County'
    elif row.get('in_mchenry', 0) == 1:
        return 'McHenry County'
    else:
        return None  # outside district / unmapped

df['banked_region'] = df.apply(assign_banked_region, axis=1)

region_order = ['Chicago', 'Suburban Cook', 'Lake County', 'McHenry County']

# ============================================================================
# AGGREGATE BY REGION
# ============================================================================

print("\nAggregating by region...")
print(f"{'Region':<22s} {'Precincts':>10s} {'Est. Turnout':>14s}")
print("-" * 50)

output = {}
total_district_turnout = df[df['banked_region'].notna()]['estimated_turnout'].sum()

for region in region_order:
    rdf = df[df['banked_region'] == region]

    if len(rdf) == 0:
        print(f"  WARNING: No precincts found for {region}")
        continue

    region_turnout = rdf['estimated_turnout'].sum()
    turnout_share_pct = (region_turnout / total_district_turnout) * 100

    # Weighted average vote share per candidate
    vote_shares = {}
    expected_votes = {}
    for cand in CANDIDATES:
        col = f'median_pct_{cand}'
        if col in rdf.columns:
            weighted_sum = (rdf[col] * rdf['estimated_turnout']).sum()
            share = (weighted_sum / region_turnout) if region_turnout > 0 else 0
            vote_shares[cand] = round(share, 2)
            expected_votes[cand] = round(region_turnout * share / 100)
        else:
            vote_shares[cand] = 0.0
            expected_votes[cand] = 0

    output[region] = {
        'expected_turnout': int(round(region_turnout)),
        'turnout_share_pct': round(turnout_share_pct, 1),
        'num_precincts': len(rdf),
        'vote_shares': vote_shares,
        'expected_votes': expected_votes
    }

    print(f"  {region:<20s} {len(rdf):>10d} {int(round(region_turnout)):>14,}")

print(f"\n  {'DISTRICT TOTAL':<20s} {'':>10s} {int(total_district_turnout):>14,}")

# ============================================================================
# WRITE JSON
# ============================================================================

final_output = {
    'regions': output,
    'district_expected_turnout': int(round(total_district_turnout))
}

with open(OUTPUT_JSON, 'w') as f:
    json.dump(final_output, f, indent=2)

print(f"\n✓ Saved regional forecast to {OUTPUT_JSON}")

# ============================================================================
# PRINT SUMMARY
# ============================================================================

print("\n" + "=" * 70)
print("REGIONAL VOTE SHARE FORECAST")
print("=" * 70)

for region in region_order:
    if region not in output:
        continue
    stats = output[region]
    print(f"\n{region} ({stats['turnout_share_pct']}% of district, ~{stats['expected_turnout']:,} votes):")
    sorted_shares = sorted(stats['vote_shares'].items(), key=lambda x: x[1], reverse=True)
    for cand, share in sorted_shares:
        exp_v = stats['expected_votes'][cand]
        print(f"  {cand:<15s} {share:>6.1f}%  (~{exp_v:,} votes)")