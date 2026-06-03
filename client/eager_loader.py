import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.coordinator import Coordinator, QueryResult
import config

def run_eager_query(latency_ms: int = 0, country: str = "United Kingdom", limit: int = 50) -> QueryResult:
    result = QueryResult()
    coordinator = Coordinator()

    authors_with_books = coordinator.get_authors_with_books(
        country=country, book_limit=limit, latency_ms=latency_ms, result=result
    )

    result.data = authors_with_books
    return result
