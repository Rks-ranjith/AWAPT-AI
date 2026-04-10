from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
import hashlib
import asyncio

class URLNormalizer:
    IGNORABLE_PARAMS = {
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
        "fbclid", "gclid", "ref", "referrer", "_ga", "mc_cid", "mc_eid",
        "timestamp", "ts", "cb", "cachebust", "v", "_",
    }

    STRUCTURAL_PARAMS = {"id", "page", "tab", "section", "type", "category", "action"}

    @classmethod
    def normalize(cls, url: str) -> str:
        parsed = urlparse(url)
        parsed = parsed._replace(fragment="")
        params = parse_qs(parsed.query, keep_blank_values=False)
        filtered = {
            k: v for k, v in params.items()
            if k.lower() not in cls.IGNORABLE_PARAMS
        }
        sorted_query = urlencode(sorted(filtered.items()), doseq=True)
        normalized = urlunparse(parsed._replace(query=sorted_query))
        return normalized.rstrip("/")

    @classmethod
    def fingerprint(cls, url: str) -> str:
        parsed = urlparse(url)
        path = cls._normalize_path(parsed.path)
        return hashlib.md5(f"{parsed.netloc}{path}".encode()).hexdigest()

    @classmethod
    def _normalize_path(cls, path: str) -> str:
        import re
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '{uuid}', path, flags=re.IGNORECASE
        )
        path = re.sub(r'/\d+(/|$)', r'/{id}\1', path)
        return path

class CrawlQueue:
    def __init__(self, max_depth: int = 5, max_urls_per_path_pattern: int = 3):
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.visited_normalized: set = set()
        self.visited_fingerprints: dict = {} 
        self.max_depth = max_depth
        self.max_urls_per_path_pattern = max_urls_per_path_pattern
        self._url_depth_map: dict = {}

    def should_visit(self, url: str, depth: int) -> bool:
        if depth > self.max_depth: return False
        normalized = URLNormalizer.normalize(url)
        if normalized in self.visited_normalized: return False
        
        fp = URLNormalizer.fingerprint(url)
        if self.visited_fingerprints.get(fp, 0) >= self.max_urls_per_path_pattern: return False
        return True

    def mark_visited(self, url: str):
        normalized = URLNormalizer.normalize(url)
        fp = URLNormalizer.fingerprint(url)
        self.visited_normalized.add(normalized)
        self.visited_fingerprints[fp] = self.visited_fingerprints.get(fp, 0) + 1

    async def add(self, url: str, depth: int, priority: int = 5):
        if self.should_visit(url, depth):
            self.mark_visited(url)
            self._url_depth_map[url] = depth
            await self.queue.put((priority, depth, url))
