import os
import sys
import json
from flask import Flask, jsonify, send_from_directory, request
import requests as http_requests
from requests.exceptions import RequestException

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NODES, get_node_urls, RESULTS_DIR
from client.coordinator import Coordinator
from client.lazy_loader import lazy_load
from client.eager_loader import eager_load

app = Flask(__name__, static_folder="web")
coordinator = Coordinator(get_node_urls(), timeout=5)


@app.route("/")
def index():
    return send_from_directory("web", "index.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory("web", filename)


@app.route("/api/overview")
def api_overview():
    node_info = []
    for i, node in enumerate(NODES):
        url = f"http://{node['host']}:{node['port']}"
        try:
            resp = http_requests.get(f"{url}/health", timeout=2)
            health = resp.json()
            cache_resp = http_requests.get(f"{url}/cache/stats", timeout=2)
            cache = cache_resp.json()
            node_info.append({
                "name": node["name"],
                "site_id": node["site_id"],
                "status": "online",
                "letter_range": f"{node['letter_range'][0]}-{node['letter_range'][1]}",
                "url": url,
                "cache": cache,
            })
        except RequestException:
            node_info.append({
                "name": node["name"],
                "site_id": node["site_id"],
                "status": "offline",
                "letter_range": f"{node['letter_range'][0]}-{node['letter_range'][1]}",
                "url": url,
            })
    return jsonify({"nodes": node_info})


@app.route("/api/query/lazy")
def api_lazy():
    country = request.args.get("country", "United Kingdom")
    limit = request.args.get("limit", 50, type=int)

    result = lazy_load(coordinator, country=country, limit=limit)

    return jsonify({
        "authors": result.data[:20],
        "stats": {
            "total_authors": len(result.data),
            "total_time_ms": round(result.total_time_ms, 2),
            "network_calls": result.network_calls,
            "total_network_ms": round(result.total_network_ms, 2),
            "total_serialization_ms": round(result.total_serialization_ms, 2),
            "failed_nodes": result.failed_nodes,
        }
    })


@app.route("/api/query/eager")
def api_eager():
    country = request.args.get("country", "United Kingdom")
    limit = request.args.get("limit", 50, type=int)

    result = eager_load(coordinator, country=country, limit=limit)

    return jsonify({
        "authors": result.data[:20],
        "stats": {
            "total_authors": len(result.data),
            "total_time_ms": round(result.total_time_ms, 2),
            "network_calls": result.network_calls,
            "total_network_ms": round(result.total_network_ms, 2),
            "total_serialization_ms": round(result.total_serialization_ms, 2),
            "total_deserialization_ms": round(result.total_deserialization_ms, 2),
            "failed_nodes": result.failed_nodes,
        }
    })


@app.route("/api/set_latency", methods=["POST"])
def api_set_latency():
    data = request.get_json()
    latency = data.get("latency_ms", 0)
    coordinator.set_latency(latency)
    return jsonify({"latency_ms": latency})


@app.route("/api/benchmark_results")
def api_benchmark():
    path = os.path.join(RESULTS_DIR, "benchmark_results.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No benchmark results found"}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
