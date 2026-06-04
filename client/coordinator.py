import requests
import sys
import os
import time
import json
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

logger = logging.getLogger(__name__)

class QueryResult:

    def __init__(self):
        self.data = []
        self.network_ms = 0.0
        self.server_serialization_ms = 0.0
        self.client_deserialization_ms = 0.0
        self.request_count = 0

    @property
    def total_rehydration_ms(self):
        # Rehydration/Serialization theory (Chapter 15.4.2)
        return self.server_serialization_ms + self.client_deserialization_ms

    @property
    def total_response_ms(self):
        return self.network_ms + self.total_rehydration_ms

    def to_dict(self):
        return {
            "author_count": len(self.data),
            "request_count": self.request_count,
            "network_ms": round(self.network_ms, 2),
            "server_serialization_ms": round(self.server_serialization_ms, 2),
            "client_deserialization_ms": round(self.client_deserialization_ms, 2),
            "total_rehydration_ms": round(self.total_rehydration_ms, 2),
            "total_response_ms": round(self.total_response_ms, 2),
        }

class Coordinator:

    def __init__(self):
        self.node_urls = config.get_node_urls()

    def _build_headers(self, latency_ms: int = 0) -> dict:
        return {'X-Simulated-Latency': str(latency_ms)}

    def _timed_request(self, method: str, url: str, result: QueryResult,
                       **kwargs) -> list:
        timeout = kwargs.pop('timeout', config.REQUEST_TIMEOUT_SEC)
        for attempt in range(config.MAX_RETRIES):
            try:
                req_start = time.perf_counter()
                response = requests.request(
                    method, url, timeout=timeout, **kwargs
                )
                network_elapsed = (time.perf_counter() - req_start) * 1000

                if response.status_code >= 500:
                    logger.warning(
                        f"Server error {response.status_code} on {url} "
                        f"(attempt {attempt + 1}/{config.MAX_RETRIES})"
                    )
                    if attempt < config.MAX_RETRIES - 1:
                        time.sleep(config.RETRY_DELAY_MS / 1000.0)
                    continue

                result.request_count += 1

                ser_ms = float(response.headers.get('X-Serialization-Ms', 0))
                result.server_serialization_ms += ser_ms

                deser_start = time.perf_counter()
                data = response.json()
                deser_ms = (time.perf_counter() - deser_start) * 1000
                result.client_deserialization_ms += deser_ms

                # pure_network = tổng thời gian chờ HTTP - thời gian server xử lý (ser_ms)
                # deser_ms không nằm trong network_elapsed vì response.json() được gọi sau
                pure_network = max(0, network_elapsed - ser_ms)
                result.network_ms += pure_network

                return data

            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Request failed for {url}: {e} "
                    f"(attempt {attempt + 1}/{config.MAX_RETRIES})"
                )
                if attempt < config.MAX_RETRIES - 1:
                    time.sleep(config.RETRY_DELAY_MS / 1000.0)

        return []

    def get_all_authors(self, latency_ms: int = 0, result: QueryResult = None, country: str = "") -> list:
        if result is None:
            result = QueryResult()
        
        all_authors = []
        headers = self._build_headers(latency_ms)
        for node_url in self.node_urls:
            params = {}
            if country:
                params['country'] = country
            authors = self._timed_request(
                'GET', f"{node_url}/authors",
                result, headers=headers, params=params
            )
            all_authors.extend(authors)
        result.data = all_authors
        return all_authors

    def get_author_books(self, author_oid: str, author_name: str,
                         limit: int = 50, latency_ms: int = 0,
                         result: QueryResult = None) -> list:
        if result is None:
            result = QueryResult()

        node_url = config.get_node_for_author(author_name)
        headers = self._build_headers(latency_ms)
        return self._timed_request(
            'GET', f"{node_url}/authors/{author_oid}/books",
            result, headers=headers, params={'limit': limit}
        )

    def get_authors_with_books(self, country: str = 'United Kingdom',
                               book_limit: int = 50,
                               latency_ms: int = 0,
                               result: QueryResult = None) -> list:
        if result is None:
            result = QueryResult()

        all_results = []
        headers = self._build_headers(latency_ms)
        for node_url in self.node_urls:
            results = self._timed_request(
                'GET', f"{node_url}/authors-with-books",
                result, headers=headers,
                params={'country': country, 'book_limit': book_limit}
            )
            all_results.extend(results)
        result.data = all_results
        return all_results

    def check_health(self) -> list:
        healthy = []
        for url in self.node_urls:
            try:
                resp = requests.get(f"{url}/health", timeout=2)
                if resp.status_code == 200:
                    healthy.append(url)
            except requests.exceptions.RequestException:
                pass
        return healthy

    def invalidate_cache(self, key: str) -> bool:
        success = True
        for url in self.node_urls:
            try:
                resp = requests.post(
                    f"{url}/cache/invalidate",
                    json={'key': key}, timeout=5
                )
                if resp.status_code != 200:
                    success = False
            except requests.exceptions.RequestException:
                success = False
        return success

    def get_metrics(self) -> list:
        metrics = []
        for url in self.node_urls:
            try:
                resp = requests.get(f"{url}/metrics", timeout=5)
                if resp.status_code == 200:
                    metrics.append(resp.json())
            except requests.exceptions.RequestException:
                pass
        return metrics
