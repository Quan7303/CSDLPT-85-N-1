import sys
import os
import json
import time
import statistics

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from client.lazy_loader import run_lazy_query
from client.eager_loader import run_eager_query

def run_benchmark():
    print("=" * 60)
    print("  Benchmark Vấn đề N+1 ")
    print("=" * 60)

    latencies = config.LATENCY_LEVELS_MS
    iterations = config.BENCHMARK_ITERATIONS

    all_results = []

    print("\n  Làm nóng hệ thống (Warm-up) để nạp Cache và DB...")
    run_eager_query(latency_ms=0)
    run_lazy_query(latency_ms=0)
    print("  Đã làm nóng xong! Bắt đầu đo lường chính thức.\n")

    for latency in latencies:
        print(f"\n  Testing latency: {latency}ms ({iterations} iterations)...")

        eager_times = []
        lazy_times = []
        eager_breakdowns = []
        lazy_breakdowns = []

        for it in range(iterations):

            eager_result = run_eager_query(latency_ms=latency)
            eager_times.append(eager_result.total_response_ms)
            eager_breakdowns.append(eager_result.to_dict())

            lazy_result = run_lazy_query(latency_ms=latency)
            lazy_times.append(lazy_result.total_response_ms)
            lazy_breakdowns.append(lazy_result.to_dict())

        eager_mean = statistics.mean(eager_times)
        lazy_mean = statistics.mean(lazy_times)
        eager_stdev = statistics.stdev(eager_times) if len(eager_times) > 1 else 0
        lazy_stdev = statistics.stdev(lazy_times) if len(lazy_times) > 1 else 0
        speedup = lazy_mean / eager_mean if eager_mean > 0 else 0

        entry = {
            "author_limit": "All",
            "latency_ms": latency,
            "iterations": iterations,
            "eager": {
                "mean_ms": round(eager_mean, 2),
                "stdev_ms": round(eager_stdev, 2),
                "request_count": eager_breakdowns[0]["request_count"],
                "avg_network_ms": round(statistics.mean(
                    [b["network_ms"] for b in eager_breakdowns]
                ), 2),
                "avg_serialization_ms": round(statistics.mean(
                    [b["server_serialization_ms"] for b in eager_breakdowns]
                ), 2),
                "avg_deserialization_ms": round(statistics.mean(
                    [b["client_deserialization_ms"] for b in eager_breakdowns]
                ), 2),
            },
            "lazy": {
                "mean_ms": round(lazy_mean, 2),
                "stdev_ms": round(lazy_stdev, 2),
                "request_count": lazy_breakdowns[0]["request_count"],
                "avg_network_ms": round(statistics.mean(
                    [b["network_ms"] for b in lazy_breakdowns]
                ), 2),
                "avg_serialization_ms": round(statistics.mean(
                    [b["server_serialization_ms"] for b in lazy_breakdowns]
                ), 2),
                "avg_deserialization_ms": round(statistics.mean(
                    [b["client_deserialization_ms"] for b in lazy_breakdowns]
                ), 2),
            },
            "speedup": round(speedup, 1),
        }
        all_results.append(entry)
        print(f"    Eager: {eager_mean:.0f}ms | Lazy: {lazy_mean:.0f}ms | "
              f"Speedup: {speedup:.1f}x")

    results_path = os.path.join(config.RESULTS_DIR, "benchmark_results.json")
    with open(results_path, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {results_path}")

    return all_results

if __name__ == '__main__':
    run_benchmark()
