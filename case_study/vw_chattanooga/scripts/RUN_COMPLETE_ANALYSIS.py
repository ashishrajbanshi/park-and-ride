"""
MASTER EXECUTION SCRIPT
Runs complete VW Chattanooga P&R analysis from start to finish
"""

import subprocess
import sys
import os
from datetime import datetime

print("="*80)
print(" VW CHATTANOOGA PARK-AND-RIDE ANALYSIS")
print(" Complete System Execution")
print("="*80)
print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Change to scripts directory
os.chdir('case_study/vw_chattanooga/scripts')

scripts = [
    ("01_filter_parking_candidates.py", "Filtering Parking Candidates"),
    ("02_calculate_accessibility_scores.py", "Calculating Accessibility Scores"),
    ("03_rank_and_optimize.py", "Ranking & Optimization"),
    ("04_user_routing_system.py", "User Routing System"),
    ("05_generate_methodology_report.py", "Generating Methodology Report")
]

results = []

for script_name, description in scripts:
    print("\n" + "="*80)
    print(f"EXECUTING: {description}")
    print(f"Script: {script_name}")
    print("="*80 + "\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            check=True,
            capture_output=False,
            text=True
        )
        results.append((script_name, "✅ SUCCESS"))
        print(f"\n✅ {description} - COMPLETE")
        
    except subprocess.CalledProcessError as e:
        results.append((script_name, "❌ FAILED"))
        print(f"\n❌ {description} - FAILED")
        print(f"Error: {e}")
        
        user_input = input("\nContinue to next step? (y/n): ")
        if user_input.lower() != 'y':
            print("\n❌ Analysis stopped by user")
            break

# Summary
print("\n" + "="*80)
print(" EXECUTION SUMMARY")
print("="*80)

for script, status in results:
    print(f"{status} {script}")

print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if all(status.startswith("✅") for _, status in results):
    print("\n🎉 ALL STEPS COMPLETED SUCCESSFULLY!")
    print("\nNext steps:")
    print("1. Open ArcGIS Pro")
    print("2. Follow visualization guide in: case_study/vw_chattanooga/docs/ARCGIS_VISUALIZATION_GUIDE.md")
    print("3. Review methodology report in: case_study/vw_chattanooga/results/reports/")
else:
    print("\n⚠️  Some steps failed. Review errors above.")