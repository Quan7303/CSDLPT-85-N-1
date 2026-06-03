import sys
import os
import time
import json

from flask import Flask, request, jsonify, make_response

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from nodes.models import Base, Author, Book
from nodes.cache_manager import DistributedCache

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

if len(sys.argv) < 2:
    print("Usage: python node_server.py <node_index>")
    sys.exit(1)

NODE_INDEX = int(sys.argv[1])
NODE_INFO = config.NODES[NODE_INDEX]

engine = create_engine(
    f"sqlite:///{NODE_INFO['db_path']}",
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(engine)

cache = DistributedCache(
    max_entries=config.CACHE_MAX_ENTRIES,
    ttl_seconds=config.CACHE_TTL_SECONDS
)

request_count = 0
total_serialization_ms = 0.0

@app.before_request
def simulate_network_latency():
    global request_count
    request_count += 1
    latency_ms = request.headers.get('X-Simulated-Latency', 0)
    try:
        latency_ms = int(latency_ms)
    except (ValueError, TypeError):
        latency_ms = 0
    if latency_ms > 0:
        time.sleep(latency_ms / 1000.0)

def _make_response_with_timing(data, serialization_ms=0.0):
    global total_serialization_ms
    start = time.perf_counter()
    body = json.dumps(data)
    ser_ms = (time.perf_counter() - start) * 1000 + serialization_ms
    total_serialization_ms += ser_ms
    resp = make_response(body)
    resp.headers['Content-Type'] = 'application/json'
    resp.headers['X-Serialization-Ms'] = f"{ser_ms:.3f}"
    return resp

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "node": NODE_INFO['name'],
        "site_id": NODE_INFO['site_id'],
        "index": NODE_INDEX,
        "letter_range": f"{NODE_INFO['letter_range'][0]}-{NODE_INFO['letter_range'][1]}",
    }), 200

@app.route('/authors', methods=['GET'])
def get_authors():
    country = request.args.get('country')

    cache_key = f"authors:{country or 'all'}"
    if config.CACHE_ENABLED:
        cached = cache.get(cache_key)
        if cached is not None:
            return _make_response_with_timing(cached)

    session = SessionLocal()
    try:
        query = session.query(Author)
        if country:
            query = query.filter(Author.country == country)
        authors = query.all()

        ser_start = time.perf_counter()
        result = [a.to_dict() for a in authors]
        ser_ms = (time.perf_counter() - ser_start) * 1000

        if config.CACHE_ENABLED:
            cache.put(cache_key, result)

        return _make_response_with_timing(result, ser_ms)
    finally:
        session.close()

@app.route('/authors/<oid>/books', methods=['GET'])
def get_author_books(oid):
    limit = request.args.get('limit', default=50, type=int)

    cache_key = f"books:{oid}:{limit}"
    if config.CACHE_ENABLED:
        cached = cache.get(cache_key)
        if cached is not None:
            return _make_response_with_timing(cached)

    session = SessionLocal()
    try:
        books = (
            session.query(Book)
            .filter(Book.author_oid == oid)
            .order_by(Book.publication_date.desc())
            .limit(limit)
            .all()
        )
        ser_start = time.perf_counter()
        result = [b.to_dict() for b in books]
        ser_ms = (time.perf_counter() - ser_start) * 1000

        if config.CACHE_ENABLED:
            cache.put(cache_key, result)

        return _make_response_with_timing(result, ser_ms)
    finally:
        session.close()

@app.route('/authors-with-books', methods=['GET'])
def get_authors_with_books():
    country = request.args.get('country')
    book_limit = request.args.get('book_limit', default=50, type=int)

    cache_key = f"authors_with_books:{country or 'all'}:{book_limit}"
    if config.CACHE_ENABLED:
        cached = cache.get(cache_key)
        if cached is not None:
            return _make_response_with_timing(cached)

    session = SessionLocal()
    try:
        query = (
            session.query(Author, Book)
            .outerjoin(Book, Author.oid == Book.author_oid)
        )
        if country:
            query = query.filter(Author.country == country)

        query = query.order_by(Author.oid, Book.publication_date.desc())
        rows = query.all()

        ser_start = time.perf_counter()
        author_map = {}
        for author, book in rows:
            if author.oid not in author_map:
                author_map[author.oid] = author.to_dict()
                author_map[author.oid]['books'] = []
            if book is not None and len(author_map[author.oid]['books']) < book_limit:
                author_map[author.oid]['books'].append(book.to_dict())
        result = list(author_map.values())
        ser_ms = (time.perf_counter() - ser_start) * 1000

        if config.CACHE_ENABLED:
            cache.put(cache_key, result)

        return _make_response_with_timing(result, ser_ms)
    finally:
        session.close()

@app.route('/cache/invalidate', methods=['POST'])
def cache_invalidate():
    data = request.get_json(force=True, silent=True)
    if not data or 'key' not in data:
        return jsonify({"error": "Missing 'key' in body"}), 400
    found = cache.invalidate(data['key'])
    return jsonify({"status": "invalidated", "key": data['key'], "was_cached": found}), 200

@app.route('/cache/stats', methods=['GET'])
def cache_stats():
    stats = cache.get_stats()
    stats["enabled"] = config.CACHE_ENABLED
    return jsonify(stats), 200

@app.route('/metrics', methods=['GET'])
def metrics():
    cache_stats_data = cache.get_stats()

    gc_count = cache.gc_sweep()

    return jsonify({
        "node": NODE_INFO['name'],
        "site_id": NODE_INFO['site_id'],
        "request_count": request_count,
        "total_serialization_ms": round(total_serialization_ms, 2),
        "avg_serialization_ms": round(total_serialization_ms / request_count, 3) if request_count > 0 else 0,
        "cache": cache_stats_data,
        "gc_sweep_collected": gc_count,
    }), 200

if __name__ == '__main__':
    print(f"Starting {NODE_INFO['name']} (site_id={NODE_INFO['site_id']}) on port {NODE_INFO['port']}...")
    print(f"  Letter range: {NODE_INFO['letter_range'][0]}-{NODE_INFO['letter_range'][1]}")
    print(f"  DB: {NODE_INFO['db_path']}")
    app.run(
        host=NODE_INFO['host'],
        port=NODE_INFO['port'],
        debug=False
    )
