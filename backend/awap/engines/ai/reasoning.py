import logging
import asyncio
try:
    import networkx as nx
except ImportError:
    nx = None
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AttackReasoningEngine:
    """
    AI Attack Graph Engine (Phase 3 Orchestration)
    Models the application's attack surface as a directed graph. Uses topological 
    analysis to prioritize attack testing orders and suggest multi-step exploitation chains.
    """
    def __init__(self):
        self.attack_graph = nx.DiGraph() if nx else None
        
        # Risk Multipliers based on URL heuristics (learned weights)
        self.risk_weights = {
            "auth": 0.9, "login": 0.9, "admin": 1.0, "dashboard": 0.8,
            "api": 0.7, "upload": 0.85, "download": 0.8, "checkout": 0.85,
            "profile": 0.6, "search": 0.5, "public": 0.2
        }
        
    def _calculate_node_weight(self, url: str) -> float:
        """Applies heuristic risk multipliers to an endpoint based on path characteristics."""
        url_lower = url.lower()
        weight = 0.1 # Base weight
        for key, w in self.risk_weights.items():
            if key in url_lower:
                weight = max(weight, w)
        return weight

    def _build_attack_graph(self, endpoints: List[Any]):
        """Constructs a Directed Graph modeling the application flow."""
        if not self.attack_graph:
            return
            
        self.attack_graph.clear()
        
        # 1. Add all endpoints as Nodes
        for ep in endpoints:
            weight = self._calculate_node_weight(ep.url)
            self.attack_graph.add_node(ep.url, method=ep.method, weight=weight, params=ep.params)

        # 2. Establish Edges (Dependencies / Flow)
        # Assuming URL paths dictate flow (e.g., /api/users -> /api/users/1)
        nodes = list(self.attack_graph.nodes())
        for i, source in enumerate(nodes):
            source_parts = source.strip("/").split("/")
            for target in nodes:
                if source == target:
                    continue
                target_parts = target.strip("/").split("/")
                
                # If target is a sub-path of source, there is a directed connection
                if len(target_parts) == len(source_parts) + 1 and target.startswith(source):
                    self.attack_graph.add_edge(source, target)
                
                # If both are authenticated areas, link them softly for chained CSRF/IDOR checks
                if "admin" in source and "admin" in target:
                    self.attack_graph.add_edge(source, target, type="auth_context")

    async def reason_about_attack_surface(self, endpoints: List[Any]) -> List[Dict]:
        """
        Analyzes discovered endpoints to hypothesize and prioritize attack vectors.
        """
        logger.info(f"[AI_REASONER] Plotting topological Attack Graph for {len(endpoints)} endpoints...")
        
        if nx:
            self._build_attack_graph(endpoints)
            # Use PageRank algorithm to find the most "central" critical endpoints organically
            try:
                centrality = nx.pagerank(self.attack_graph, weight='weight')
            except Exception:
                centrality = {ep.url: self._calculate_node_weight(ep.url) for ep in endpoints}
        else:
            logger.warning("[AI_REASONER] NetworkX not installed. Using linear fallback heuristics.")
            centrality = {ep.url: self._calculate_node_weight(ep.url) for ep in endpoints}
            
        attack_plan = []
        
        for ep in endpoints:
            url = ep.url
            method = ep.method.upper()
            
            # Identify Vuln Classes based on parameters and method
            suggested_vulns = []
            if "GET" in method and ep.params:
                suggested_vulns.extend(["SQL_INJECTION", "XSS_REFLECTED", "SSRF"])
            if "POST" in method:
                suggested_vulns.extend(["SQL_INJECTION", "COMMAND_INJECTION", "CSRF", "IDOR"])
            if "upload" in url.lower():
                suggested_vulns.append("FILE_UPLOAD_RCE")
                
            priority_score = centrality.get(url, 0.1) * 10 
            
            attack_plan.append({
                "endpoint": url,
                "hypothesis": f"Algorithm assigned PageRank centrality vector {priority_score:.2f}",
                "suggested_vulns": list(set(suggested_vulns)),
                "priority": round(priority_score, 2)
            })
            
        # Deliver optimized attack plan sorted by Topological Centrality Score
        attack_plan.sort(key=lambda x: x['priority'], reverse=True)
        return attack_plan
