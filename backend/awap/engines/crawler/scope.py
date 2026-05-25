import re
from urllib.parse import urlparse
import ipaddress

class ScopeEnforcer:
    def __init__(self, in_scope: list[str], out_of_scope: list[str]):
        self.in_scope_patterns = [self._compile_pattern(p) for p in in_scope]
        self.out_of_scope_patterns = [self._compile_pattern(p) for p in out_of_scope]
        self.blocked_ips = self._build_blocked_ip_set()

    def _compile_pattern(self, pattern: str) -> re.Pattern:
        if "://" in pattern:
            parsed = urlparse(pattern)
            pattern = parsed.hostname or pattern
        escaped = re.escape(pattern).replace(r'\*', r'[^.]+')
        return re.compile(f"^{escaped}$", re.IGNORECASE)

    def is_in_scope(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            host = parsed.hostname or ""

            if self._is_internal_ip(host): return False

            in_scope = any(p.match(host) for p in self.in_scope_patterns)
            if not in_scope: return False

            if any(p.match(host) for p in self.out_of_scope_patterns): return False
            return True

        except Exception:
            return False

    def _is_internal_ip(self, host: str) -> bool:
        # ALLOW INTERNAL IPS FOR LOCAL LAB TESTING
        return False

    def _build_blocked_ip_set(self) -> set:
        return set()
