import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sqlalchemy import create_engine

DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"
engine = create_engine(DB_CONNECTION)

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300

print("📊 GENERATING FINAL VISUALIZATIONS\n")

# Load results
df = pd.read_sql("SELECT * FROM parking_accessibility_scores ORDER BY rank", engine)

# ============================================
# CHART 1: Top 10 Sites Bar Chart
# ============================================
fig, ax = plt.subplots(figsize=(12, 8))
top10 = df.head(10)

bars = ax.barh(top10['name'], top10['composite_score'], color='steelblue')

# Color code by supply-demand status
colors = {'High Demand - Undersupplied': 'red',
          'Adequate Demand - Consider Expansion': 'orange',
          'Balanced': 'green',
          'Low Demand - Oversupplied': 'gray'}

for i, (idx, row) in enumerate(top10.iterrows()):
    bars[i].set_color(colors.get(row['supply_demand_status'], 'steelblue'))

ax.set_xlabel('Composite Accessibility Score', fontsize=12, fontweight='bold')
ax.set_title('Top 10 Park & Ride Sites by Accessibility Score', 
             fontsize=14, fontweight='bold', pad=20)
ax.grid(axis='x', alpha=0.3)

# Add legend for status
from matplotlib.patches import Patch
legend_elements = [Patch(facecolor=color, label=status) 
                   for status, color in colors.items()]
ax.legend(handles=legend_elements, loc='lower right', title='Supply-Demand Status')

plt.tight_layout()
plt.savefig('results/top10_sites.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/top10_sites.png")

# ============================================
# CHART 2: Demand vs Capacity Scatter
# ============================================
fig, ax = plt.subplots(figsize=(12, 8))

scatter = ax.scatter(df['estimated_demand'], df['capacity'], 
                     c=df['composite_score'], s=200, 
                     cmap='RdYlGn', alpha=0.7, edgecolors='black')

# Add 1:1 line (perfect balance)
max_val = max(df['estimated_demand'].max(), df['capacity'].max())
ax.plot([0, max_val], [0, max_val], 'k--', alpha=0.3, label='Perfect Balance')

# Label top 5 sites
top5 = df.head(5)
for idx, row in top5.iterrows():
    ax.annotate(row['name'], 
                (row['estimated_demand'], row['capacity']),
                xytext=(10, 10), textcoords='offset points',
                fontsize=9, alpha=0.8,
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0'))

ax.set_xlabel('Estimated Demand (users/day)', fontsize=12, fontweight='bold')
ax.set_ylabel('Parking Capacity (spaces)', fontsize=12, fontweight='bold')
ax.set_title('Park & Ride Supply vs Demand Analysis', 
             fontsize=14, fontweight='bold', pad=20)

cbar = plt.colorbar(scatter, ax=ax)
cbar.set_label('Accessibility Score', rotation=270, labelpad=20, fontweight='bold')

ax.legend()
ax.grid(alpha=0.3)

plt.tight_layout()
plt.savefig('results/supply_demand_scatter.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/supply_demand_scatter.png")

# ============================================
# CHART 3: Score Components Radar Chart
# ============================================
from math import pi

top5_sites = df.head(5)
categories = ['Demand', 'Transit\nAccess', 'Transit\nFrequency', 
              'Capacity', 'Proximity']

fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))

angles = [n / float(len(categories)) * 2 * pi for n in range(len(categories))]
angles += angles[:1]

for idx, row in top5_sites.iterrows():
    values = [row['demand_score'], row['transit_access_score'], 
              row['transit_frequency_score'], row['capacity_score'], 
              row['proximity_score']]
    values += values[:1]
    
    ax.plot(angles, values, 'o-', linewidth=2, label=row['name'])
    ax.fill(angles, values, alpha=0.15)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, size=10)
ax.set_ylim(0, 100)
ax.set_title('Top 5 Sites: Multi-Dimensional Performance', 
             size=14, fontweight='bold', y=1.08)
ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
ax.grid(True)

plt.tight_layout()
plt.savefig('results/radar_chart_top5.png', dpi=300, bbox_inches='tight')
print("✓ Saved: results/radar_chart_top5.png")

# ============================================
# STATISTICS SUMMARY
# ============================================
print("\n📈 SUMMARY STATISTICS:\n")
print(f"Total parking sites analyzed: {len(df)}")
print(f"Total parking capacity: {df['capacity'].sum():,.0f} spaces")
print(f"Total estimated demand: {df['estimated_demand'].sum():,.0f} users")
print(f"Average composite score: {df['composite_score'].mean():.2f}")
print(f"\nSupply-Demand Distribution:")
print(df['supply_demand_status'].value_counts())

# Export summary table
summary = df[['rank', 'name', 'composite_score', 'estimated_demand', 
              'capacity', 'transit_stops_nearby', 'supply_demand_status']].head(20)
summary.to_csv('results/top20_summary.csv', index=False)
print("\n✓ Saved: results/top20_summary.csv")

print("\n✅ ALL ANALYSIS COMPLETE!")
print("\nYour final deliverables are in the 'results/' folder:")
print("  • parking_rankings.csv (full results)")
print("  • top20_summary.csv (top sites)")
print("  • top10_sites.png")
print("  • supply_demand_scatter.png")
print("  • radar_chart_top5.png")
print("  • chattanooga_parkride_map.pdf (from ArcGIS Pro)")