import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

NODES = [
    {
        "name": "Node_A",
        "site_id": "A",
        "host": "127.0.0.1",
        "port": 5001,
        "db_path": os.path.join(BASE_DIR, "nodes", "node_a.db"),
        "letter_range": ("A", "H"),
    },
    {
        "name": "Node_B",
        "site_id": "B",
        "host": "127.0.0.1",
        "port": 5002,
        "db_path": os.path.join(BASE_DIR, "nodes", "node_b.db"),
        "letter_range": ("I", "P"),
    },
    {
        "name": "Node_C",
        "site_id": "C",
        "host": "127.0.0.1",
        "port": 5003,
        "db_path": os.path.join(BASE_DIR, "nodes", "node_c.db"),
        "letter_range": ("Q", "Z"),
    },
]

def get_node_index(name: str) -> int:
    first_char = name[0].upper()
    for i, node in enumerate(NODES):
        start, end = node["letter_range"]
        if start <= first_char <= end:
            return i
    return len(NODES) - 1

def get_node_urls() -> list:
    return [f"http://{n['host']}:{n['port']}" for n in NODES]

def get_node_url(index: int) -> str:
    n = NODES[index]
    return f"http://{n['host']}:{n['port']}"

def get_node_for_author(author_name: str) -> str:
    idx = get_node_index(author_name)
    return get_node_url(idx)

TOTAL_AUTHORS = 300
BOOKS_PER_AUTHOR = 100
AUTHOR_LIMIT = 50

CACHE_ENABLED = True
CACHE_TTL_SECONDS = 300
CACHE_MAX_ENTRIES = 1000

SERIALIZATION_FORMAT = "json"

LATENCY_LEVELS_MS = [0, 10, 20, 50, 100, 200]
BENCHMARK_ITERATIONS = 2

MAX_RETRIES = 3
RETRY_DELAY_MS = 200
REQUEST_TIMEOUT_SEC = 10

RESULTS_DIR = os.path.join(BASE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = "INFO"
