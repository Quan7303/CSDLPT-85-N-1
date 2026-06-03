import os
import sys
import json
from flask import Flask, jsonify, send_from_directory, request
import requests as http_requests
from requests.exceptions import RequestException

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import NODES, get_node_urls, RESULTS_DIR
from client.lazy_loader import run_lazy_query
from client.eager_loader import run_eager_query
import time

app = Flask(__name__, static_folder="web")
current_latency = 0


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
    global current_latency
    country = request.args.get('country', 'United Kingdom')
    if country == 'ALL': country = ""
    limit = request.args.get('limit', default=50, type=int)

    start = time.perf_counter()
    result = run_lazy_query(latency_ms=current_latency, country=country, limit=limit)
    total_time_ms = (time.perf_counter() - start) * 1000

    # Sort authors alphabetically to ensure order matches between Lazy and Eager
    sorted_authors = sorted(result.data, key=lambda x: x.get("name", ""))

    return jsonify({
        "authors": sorted_authors,
        "stats": {
            "total_authors": len(result.data),
            "total_time_ms": round(total_time_ms, 2),
            "network_calls": result.request_count,
            "total_network_ms": round(result.network_ms, 2),
            "total_serialization_ms": round(result.server_serialization_ms, 2),
            "total_deserialization_ms": round(result.client_deserialization_ms, 2),
            "failed_nodes": [],
        }
    })


@app.route("/api/query/eager")
def api_eager():
    global current_latency
    country = request.args.get('country', 'United Kingdom')
    if country == 'ALL': country = ""
    limit = request.args.get('limit', default=50, type=int)

    start = time.perf_counter()
    result = run_eager_query(latency_ms=current_latency, country=country, limit=limit)
    total_time_ms = (time.perf_counter() - start) * 1000

    # Sort authors alphabetically to ensure order matches between Lazy and Eager
    sorted_authors = sorted(result.data, key=lambda x: x.get("name", ""))

    return jsonify({
        "authors": sorted_authors,
        "stats": {
            "total_authors": len(result.data),
            "total_time_ms": round(total_time_ms, 2),
            "network_calls": result.request_count,
            "total_network_ms": round(result.network_ms, 2),
            "total_serialization_ms": round(result.server_serialization_ms, 2),
            "total_deserialization_ms": round(result.client_deserialization_ms, 2),
            "failed_nodes": [],
        }
    })


@app.route("/api/set_latency", methods=["POST"])
def api_set_latency():
    global current_latency
    data = request.get_json()
    current_latency = data.get("latency_ms", 0)
    return jsonify({"latency_ms": current_latency})


@app.route("/api/benchmark_results")
def api_benchmark():
    path = os.path.join(RESULTS_DIR, "benchmark_results.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    return jsonify({"error": "No benchmark results found"}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)
