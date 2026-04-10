import asyncio
import httpx
import logging
import math
from typing import List, Set, Tuple

logger = logging.getLogger(__name__)

class ParameterFuzzer:
    """
    Arjun-style Asynchronous Parameter Discovery Engine.
    Uses chunking and binary search to identify hidden GET/POST parameters
    that affect the application's response mathematically.
    """
    def __init__(self, target_url: str):
        self.target_url = target_url
        self.client = httpx.AsyncClient(limits=httpx.Limits(max_connections=30), verify=False, timeout=10.0)
        
        # Wordlist of high-value hidden parameters commonly found in bug bounty
        self.wordlist = [
            "admin", "debug", "test", "id", "user_id", "dir", "cmd", "exec", 
            "file", "path", "url", "redirect", "next", "role", "email", 
            "username", "password", "token", "API_KEY", "secret", "config", 
            "env", "format", "v", "version", "page", "api", "query", "search"
        ] * 3 # In a real scenario, this would load a 25k wordlist file
        
        # Unique parameters deduplicated
        self.wordlist = list(set(self.wordlist))

    async def get_baseline(self, method: str) -> Tuple[int, int]:
        """Establish the baseline HTTP status and response length."""
        try:
            if method == "GET":
                resp = await self.client.get(self.target_url)
            else:
                resp = await self.client.post(self.target_url)
            return resp.status_code, len(resp.content)
        except Exception as e:
            logger.error(f"Fuzzer failed to establish baseline: {e}")
            return 0, 0

    def _is_anomaly(self, base_status: int, base_len: int, resp: httpx.Response) -> bool:
        """Determines if a response deviates meaningfully from the baseline."""
        if resp.status_code != base_status:
            return True
        
        length_diff = abs(len(resp.content) - base_len)
        # If difference is more than 50 bytes or 5%, it's likely an anomaly
        if length_diff > 50 and length_diff > (base_len * 0.05):
            return True
            
        return False

    async def _test_chunk(self, chunk: List[str], method: str) -> bool:
        """Sends a chunk of parameters and returns True if it triggered an anomaly."""
        payload = {param: "awap_probe_1337" for param in chunk}
        try:
            if method == "GET":
                resp = await self.client.get(self.target_url, params=payload)
            else:
                resp = await self.client.post(self.target_url, data=payload)
                
            return self._is_anomaly(self.base_status, self.base_len, resp)
        except Exception:
            return False

    async def _binary_search(self, chunk: List[str], method: str) -> List[str]:
        """
        Recursively splits a chunk matching an anomaly to isolate the exact 
        parameter(s) causing the difference.
        """
        valid_params = []
        if len(chunk) == 1:
            if await self._test_chunk(chunk, method):
                valid_params.append(chunk[0])
            return valid_params

        mid = len(chunk) // 2
        left_half = chunk[:mid]
        right_half = chunk[mid:]

        # Test left
        if await self._test_chunk(left_half, method):
            valid_params.extend(await self._binary_search(left_half, method))
        
        # Test right
        if await self._test_chunk(right_half, method):
            valid_params.extend(await self._binary_search(right_half, method))

        return valid_params

    async def run(self, method: str = "GET") -> List[str]:
        """
        Executes the chunked parameter discovery.
        """
        logger.info(f"[PARAM_FUZZER] Starting hidden parameter discovery on {self.target_url} via {method}")
        self.base_status, self.base_len = await self.get_baseline(method)
        
        if self.base_status == 0:
            return []

        discovered_parameters = []
        chunk_size = 50 # Send 50 params at once to minimize requests
        
        chunks = [self.wordlist[i:i + chunk_size] for i in range(0, len(self.wordlist), chunk_size)]
        
        # Concurrently test all main chunks
        tasks = [self._test_chunk(chunk, method) for chunk in chunks]
        results = await asyncio.gather(*tasks)
        
        # For any chunk that triggered an anomaly, dive deep to isolate the parameter
        for i, chunk_has_anomaly in enumerate(results):
            if chunk_has_anomaly:
                logger.info(f"[PARAM_FUZZER] Anomaly detected in chunk {i}, isolating parameters...")
                isolated = await self._binary_search(chunks[i], method)
                discovered_parameters.extend(isolated)
                
        logger.info(f"[PARAM_FUZZER] Found {len(discovered_parameters)} hidden parameters.")
        return list(set(discovered_parameters))

    async def close(self):
        await self.client.aclose()
