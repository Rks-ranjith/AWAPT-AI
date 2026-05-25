import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class AILogicEngine:
    """
    Core LLM Orchestration Engine for AWAP-AI.
    Handles Vulnerability Classification, Remediation Writing, and Payload Mutation.
    """
    def __init__(self, provider: str | None = None, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        from awap.core.config import settings
        self.provider = (provider or settings.LLM_PROVIDER or "anthropic").lower()
        self.api_key = api_key or settings.LLM_API_KEY
        self.base_url = base_url or settings.LLM_BASE_URL
        
        # Resolve default models
        default_model = "gemini-2.5-flash"
        if self.provider == "openai":
            default_model = "gpt-4o"
        elif self.provider == "anthropic":
            default_model = "claude-3-5-sonnet-20241022"
            
        self.model = model or settings.LLM_MODEL or default_model
        
        # Instantiate clients dynamically based on settings
        if self.provider == "anthropic":
            from anthropic import AsyncAnthropic
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = AsyncAnthropic(**kwargs)
        elif self.provider == "openai":
            from openai import AsyncOpenAI
            kwargs = {"api_key": self.api_key}
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self.client = AsyncOpenAI(**kwargs)
        elif self.provider in ("gemini", "google"):
            if self.base_url:
                from openai import AsyncOpenAI
                self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            else:
                self.client = None
        else:
            self.client = None

    async def _dispatch_prompt(self, system_prompt: str, user_prompt: str, max_tokens: int = 1000) -> str:
        """Helper to seamlessly route requests to the configured LLM API."""
        if not self.api_key:
            logger.warning("[LLM] API Key not configured. Returning fallback.")
            raise ValueError("No LLM API Key configured.")

        # Native Gemini API call (zero-dependency REST over HTTP)
        if self.provider in ("gemini", "google") and not self.base_url:
            import httpx
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
            headers = {"Content-Type": "application/json"}
            generation_config = {
                "maxOutputTokens": max(max_tokens, 4096)
            }
            if self.model.startswith("gemini-2.5"):
                generation_config["thinkingConfig"] = {
                    "thinkingBudget": 0
                }

            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": user_prompt}
                        ]
                    }
                ],
                "generationConfig": generation_config
            }
            if system_prompt:
                payload["systemInstruction"] = {
                    "parts": [
                        {"text": system_prompt}
                    ]
                }
            
            # Configure JSON mode if expected
            if "json" in system_prompt.lower() or "json" in user_prompt.lower():
                payload["generationConfig"]["responseMimeType"] = "application/json"

            try:
                async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("No candidates returned from Gemini API")
                    
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if not parts:
                        raise ValueError("No text parts returned from Gemini API")
                        
                    return parts[0].get("text", "")
            except Exception as e:
                logger.error(f"[LLM] Gemini native API call failed: {e}")
                raise e

        # Standard client libraries
        if not self.client:
            logger.warning("[LLM] API Client not initialized. Returning fallback.")
            raise ValueError("No LLM Client configured.")

        try:
            if self.provider == "anthropic":
                response = await self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}]
                )
                return response.content[0].text
            elif self.provider == "openai" or (self.provider in ("gemini", "google") and self.base_url):
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[LLM] API communication failed ({self.provider}): {e}")
            raise e
            
        return ""

    async def analyze_and_score_finding(self, finding_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Takes raw technical evidence from the Attack Engine and returns a 
        board-ready Vulnerability Report with CVSS 3.1 Scoring.
        """
        system = (
            "You are an elite Application Security Engineer analyzing output from an automated pentesting tool. "
            "Your job is to objectively analyze the provided technical evidence, explain the vulnerability mechanism clearly, "
            "calculate a strict CVSS 3.1 base score, and provide actionable remediation steps targeting developers. "
            "You must output ONLY valid, parsable JSON matching the exact schema."
        )

        user_prompt = f"""
        Evidence Block:
        {json.dumps(finding_data, indent=2)}

        Return a JSON object with EXACTLY these keys:
        - "cvss_vector": (string) e.g., "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"
        - "cvss_score": (float) e.g., 9.8
        - "severity": (string) "CRITICAL", "HIGH", "MEDIUM", or "LOW"
        - "executive_summary": (string, 2 sentences explaining risk)
        - "technical_analysis": (string, detailed breakdown of how the payload executed)
        - "remediation_guidance": (string, code-level fix instructions)
        """

        try:
            response_text = await self._dispatch_prompt(system, user_prompt, max_tokens=1500)
            
            # Extract JSON block even if model wraps in markdown
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            else:
                json_str = response_text.strip("` \n")
                
            return json.loads(json_str)
        except Exception as e:
            logger.warning(f"[LLM] Fallback triggered for finding analysis: {e}")
            # Fallback Schema
            return {
                "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
                "cvss_score": 5.0,
                "severity": "MEDIUM",
                "executive_summary": "An anomaly was detected on the endpoint.",
                "technical_analysis": f"The payload elicited a response indicating a potential {finding_data.get('vuln_class', 'vulnerability')}.",
                "remediation_guidance": "Implement strict input validation and parameterization."
            }

    async def analyze_waf_block(self, response_text: str, headers: Dict[str, str], payload: str) -> Dict[str, Any]:
        """
        Analyze a WAF error response to determine the mechanism of the block
        and suggest next-step payload evasion techniques.
        """
        system = "You are a WAF evasion specialist."
        user_prompt = f"""
        Payload Sent: {payload}
        Headers: {json.dumps(headers)}
        Body Snippet: {response_text[:500]}
        
        Analyze the likely WAF vendor and the specific signature that tripped.
        Output in JSON with keys: 'vendor', 'tripped_signature', and 'evasion_strategy'.
        """
        
        try:
            response_text = await self._dispatch_prompt(system, user_prompt, max_tokens=300)
            json_str = response_text.replace("```json", "").replace("```", "").strip()
            return json.loads(json_str)
        except Exception:
            return {
                "vendor": "Unknown Firewall",
                "tripped_signature": "Generic payload block",
                "evasion_strategy": "Try unicode encoding or alternative DOM events."
            }

    async def generate_mutations(self, vulnerability_class: str, context: Dict[str, Any], strategy: str) -> List[str]:
        """
        Generates semantic mutations for a payload to bypass filters based on 
        the provided evasion strategy.
        """
        system = "You are an expert payload developer."
        user_prompt = f"""
        Class: {vulnerability_class}
        Context Rules: {json.dumps(context)}
        Strategy: {strategy}
        
        Generate exactly 3 extremely advanced, highly evasive payload strings designed to bypass WAFs.
        Return ONLY a raw JSON array of strings. 
        """
        
        try:
            response_text = await self._dispatch_prompt(system, user_prompt, max_tokens=300)
            json_str = response_text.replace("```json", "").replace("```", "").strip()
            payloads = json.loads(json_str)
            if isinstance(payloads, list):
                return payloads
        except Exception:
            pass
            
        return []
