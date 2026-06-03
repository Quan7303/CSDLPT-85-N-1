import sys
import os
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

def load_results():
    path = os.path.join(config.RESULTS_DIR, "benchmark_results.json")
    with open(path, 'r') as f:
        data = json.load(f)
        if isinstance(data, list):
            return data, {}
        return data['results'], data.get('benchmark_config', {})

def plot_latency_comparison(results, author_limit=50):
    
    latencies = [r['latency_ms'] for r in results]
    eager = [r['eager'].get('mean_ms', r['eager'].get('avg_total_ms', 0)) for r in results]
    lazy = [r['lazy'].get('mean_ms', r['lazy'].get('avg_total_ms', 0)) for r in results]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(latencies, eager, 'o-', color='#2ecc71', linewidth=2.5,
            markersize=8, label='Eager Loading (3 requests)')
    ax.plot(latencies, lazy, 's-', color='#e74c3c', linewidth=2.5,
            markersize=8, label=f'Lazy Loading (3 + N requests)')

    ax.set_xlabel('Simulated Network Latency (ms)', fontsize=12)
    ax.set_ylabel('Total Execution Time (ms)', fontsize=12)
    ax.set_title('N+1 Problem: Lazy vs Eager Loading\n'
                 '(All UK Authors, 50 Books each)',
                 fontsize=14, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'{x:,.0f}'))

    for i, r in enumerate(results):
        if r['speedup'] > 1.5:
            ax.annotate(f"{r['speedup']}x",
                        xy=(latencies[i], lazy[i]),
                        xytext=(10, 10), textcoords='offset points',
                        fontsize=9, color='#e74c3c', fontweight='bold')

    plt.tight_layout()
    path = os.path.join(config.RESULTS_DIR, "n_plus_1_graph.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Chart 1 saved: {path}")

def plot_rehydration_breakdown(results, author_limit=50):
    
    latencies = [str(r['latency_ms']) for r in results]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    for idx, strategy in enumerate(['eager', 'lazy']):
        ax = axes[idx]
        net = [r[strategy].get('avg_network_ms', 0) for r in results]
        ser = [r[strategy].get('avg_serialization_ms', 0) for r in results]
        # Calculate deserialization or fallback
        deser = [r[strategy].get('avg_deserialization_ms', 0) for r in results]

        x = range(len(latencies))
        ax.bar(x, net, label='Network I/O', color='#3498db')
        ax.bar(x, ser, bottom=net, label='Serialization (server)', color='#e67e22')
        ax.bar(x, deser,
               bottom=[n + s for n, s in zip(net, ser)],
               label='Deserialization (client)', color='#9b59b6')

        ax.set_xlabel('Latency (ms)')
        ax.set_ylabel('Time (ms)')
        ax.set_title(f'{strategy.title()} Loading — Rehydration Cost',
                     fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(latencies)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Object Rehydration Cost Breakdown (§15.4)',
                 fontsize=13, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(config.RESULTS_DIR, "rehydration_breakdown.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Chart 2 saved: {path}")

def plot_speedup(results, author_limit=50):
    
    latencies = [str(r['latency_ms']) for r in results]
    speedups = [r['speedup'] for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))
    colors = ['#2ecc71' if s < 5 else '#e67e22' if s < 15 else '#e74c3c'
              for s in speedups]
    bars = ax.bar(latencies, speedups, color=colors, edgecolor='white')

    for bar, s in zip(bars, speedups):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f'{s:.1f}x', ha='center', fontweight='bold', fontsize=10)

    ax.set_xlabel('Network Latency (ms)')
    ax.set_ylabel('Speedup (Lazy Time / Eager Time)')
    ax.set_title('Eager Loading Speedup Over Lazy Loading',
                 fontweight='bold', fontsize=13)
    ax.axhline(y=1, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    path = os.path.join(config.RESULTS_DIR, "speedup_chart.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Chart 3 saved: {path}")

def main():
    print("=" * 60)
    print("  Generating Charts...")
    print("=" * 60)

    results, config_data = load_results()
    target = config_data.get('author_limit', 50)

    plot_latency_comparison(results, target)
    plot_rehydration_breakdown(results, target)
    plot_speedup(results, target)

    print("\n  All charts generated!")

if __name__ == '__main__':
    main()
