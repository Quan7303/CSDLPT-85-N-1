import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from client.coordinator import Coordinator, QueryResult
import config

def run_lazy_query(latency_ms: int = 0) -> QueryResult:
    result = QueryResult()
    coordinator = Coordinator()

    authors = coordinator.get_all_authors_uk(latency_ms, result)

    authors_with_books = []
    for author in authors:
        books = coordinator.get_author_books(
            author['oid'], author['name'],
            limit=config.AUTHOR_LIMIT,
            latency_ms=latency_ms,
            result=result
        )
        author_copy = author.copy()
        author_copy['books'] = books
        authors_with_books.append(author_copy)

    result.data = authors_with_books
    return result
