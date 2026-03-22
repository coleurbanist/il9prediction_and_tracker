import subprocess
import os
#runs all the necessary programs to get an updated map
print("=" * 70)
print("IL-09 PRIMARY ELECTION ANALYSIS - FULL PIPELINE")
print("=" * 70)

# Step 1: Run district-wide Monte Carlo
print("\n[1/3] Running district-wide Monte Carlo simulation...")
subprocess.run(["python", "win_probability_simulator.py"], check=True)

# Step 2: Run precinct-level simulations
print("\n[2/3] Running precinct-level simulations...")
subprocess.run(["python", "win_probability_precinct.py"], check=True)

# Step 3: Create interactive map
print("\n[3/3] Creating interactive map...")
subprocess.run(["python", "precinct_probablities_interactive_map.py"], check=True)

print("\n" + "=" * 70)
print("FULL ANALYSIS COMPLETE!")
print("=" * 70)
print("\nOutputs:")
print("  - poll_baseline.json (polling forecast)")
print("  - district_win_probabilities.json (district win odds)")
print("  - IL_09_precinct_probabilities.csv (precinct results)")
print("  - IL09_precinct_map.html (interactive map)")
print("\nOpen IL09_precinct_map.html in your browser to explore results!")