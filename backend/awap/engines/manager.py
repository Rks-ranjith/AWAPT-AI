import asyncio
import logging
import json
import httpx
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from awap.models.scan import Scan, ScanStatus
from awap.models.finding import Finding
from awap.models.target import Target
from awap.core.database import AsyncSessionLocal
from awap.engines.recon.base import ReconEngine
from awap.engines.crawler.base import CrawlerEngine
from awap.engines.crawler.fuzzer import ParameterFuzzer
from awap.engines.ai.classifier import VulnClassifier
from awap.engines.ai.llm import AILogicEngine
from awap.engines.ai.reasoning import AttackReasoningEngine
from awap.core.config import settings

# Used to publish live findings to Redis Streams
try:
    import redis.asyncio as redis
except ImportError:
    import redis

logger = logging.getLogger(__name__)

class ScanManager:
    """
    Central Autonomous Attack Orchestrator (Industrial Grade).
    Handles phase transitions, concurrent attack dispatch, and live Redis stream updates.
    """
    def __init__(self, scan_id: int):
        self.scan_id = scan_id
        self.classifier = VulnClassifier()
        self.llm_engine = AILogicEngine(provider=settings.LLM_PROVIDER, api_key=settings.LLM_API_KEY)
        self.reasoner = AttackReasoningEngine()
        
        # Redis connection for Live Stream bus
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        # Prevent completely overwhelming target
        self.concurrency_limit = asyncio.Semaphore(settings.MAX_CONCURRENT_CONNECTIONS or 20)

    async def _publish_live_stream(self, phase: str, message: str, meta: dict = None):
        """Asynchronously publish status to the Redis Message Bus for live UI."""
        payload = {"scan_id": self.scan_id, "phase": phase, "message": message, "timestamp": str(datetime.utcnow())}
        if meta:
            payload.update(meta)
            
        try:
            await self.redis_client.xadd(f"livestream:scan:{self.scan_id}", {"data": json.dumps(payload)})
        except Exception as e:
            logger.error(f"[REDIS] Failed to publish stream: {e}")

    async def run_scan(self):
        async with AsyncSessionLocal() as db:
            try:
                # Fetch scan and target
                res_scan = await db.execute(select(Scan).filter(Scan.id == self.scan_id))
                scan = res_scan.scalars().first()
                if not scan: return

                res_target = await db.execute(select(Target).filter(Target.id == scan.target_id))
                target = res_target.scalars().first()
                if not target:
                    scan.status = ScanStatus.FAILED
                    await db.commit()
                    return

                await self._publish_live_stream("RECON", f"Initiating industry-grade reconnaissance for {target.base_url}")
                
                # Phase 1: Recon
                scan.current_phase = "RECONNAISSANCE"
                await db.commit()
                await self._publish_live_stream("RECON", f"Initiating industry-grade reconnaissance for {target.base_url}")
                recon = ReconEngine(target.base_url)
                recon_results = await recon.run()
                await self._publish_live_stream("RECON", f"Discovered IP: {recon_results.get('ips')} | Open Ports: {recon_results.get('open_ports')}")
                
                # Phase 2: Crawler
                scan.current_phase = "CRAWLING"
                await db.commit()
                await self._publish_live_stream("CRAWL", "Executing deep JS-capable headless crawler...")
                crawler = CrawlerEngine(target.base_url)
                endpoints = await crawler.run()
                
                # Phase 2.5: Parameter Discovery
                await self._publish_live_stream("PARAM_FUZZ", "Initializing Arjun-style Parameter Fuzzer...")
                fuzzer = ParameterFuzzer(target.base_url)
                hidden_params = await fuzzer.run(method="GET")
                
                scan.endpoints_discovered = len(endpoints)
                await db.commit()
                
                # Phase 3: AI Reasoning
                scan.current_phase = "AI_PLANNING"
                await db.commit()
                await self._publish_live_stream("AI_REASONING", "Engaging Neural Engine to plot attack graph...")
                attack_plan = await self.reasoner.reason_about_attack_surface(endpoints)
                
                # Phase 4 & 5: Attack Injection (Synchronized Client)
                scan.current_phase = "VULN_EXPLOITATION"
                await db.commit()
                await self._publish_live_stream("ATTACK", f"Synchronized concurrent attack modules. Dispatching vectors.")
                
                from awap.modules.xss_dom import XSSModule
                from awap.modules.sqli_error import SQLiErrorModule
                from awap.modules.cmd_injection import CommandInjectionModule
                from awap.engines.attack.base import Endpoint as ModuleEndpoint, Parameter, ParameterProfile
                
                active_findings = []
                
                async with httpx.AsyncClient(verify=False, timeout=12.0) as client:
                    xss_module = XSSModule(None, client)
                    sqli_module = SQLiErrorModule(None, client)
                    cmd_module = CommandInjectionModule(None, client)
                    
                    async def execute_module_wrap(module, mod_ep, param, profile):
                        async with self.concurrency_limit:
                            try:
                                return await module.run(endpoint=mod_ep, param=param, profile=profile)
                            except Exception as e:
                                logger.warning(f"[MODULE] Failed {module.module_id} on {mod_ep.url}: {e}")
                                return []

                    tasks = []
                    for ep in endpoints:
                        mod_ep = ModuleEndpoint(url=ep.url, method=ep.method)
                        all_params = list(ep.params) + hidden_params
                        for p_name in all_params:
                            param = Parameter(name=p_name, location="query" if ep.method.upper() == "GET" else "form", original_value="", endpoint_id=ep.url)
                            profile = ParameterProfile(param_name=p_name, baseline_status=200, baseline_length=0, baseline_time=0)
                            
                            tasks.append(execute_module_wrap(sqli_module, mod_ep, param, profile))
                            tasks.append(execute_module_wrap(xss_module, mod_ep, param, profile))
                            tasks.append(execute_module_wrap(cmd_module, mod_ep, param, profile))

                    raw_findings = await asyncio.gather(*tasks, return_exceptions=True)
                    
                    total_requests = 0
                    for res in raw_findings:
                        if isinstance(res, list):
                            total_requests += len(res) * 3 # heuristic for 3 modules
                            for f in res:
                                active_findings.append(f)
                                await self._publish_live_stream("FINDING", f"CRITICAL: Identified {f.vuln_class} at {f.endpoint}", meta={"severity": f.severity})

                scan.requests_sent += total_requests
                scan.current_phase = "REPORTING"
                await db.commit()

                # Phase 6: Parallel AI Synthesis
                if active_findings:
                    await self._publish_live_stream("ANALYSIS", f"Offloading {len(active_findings)} findings to AI Synthesis layer...")
                    
                    async def process_finding(f):
                        try:
                            # AI result baseline
                            ai_result = self.classifier.classify(f.vuln_class, f.response_raw or "")
                            if ai_result["confidence"] > 0.0:
                                 finding_data = {
                                    "vuln_class": f.vuln_class,
                                    "endpoint": f.endpoint,
                                    "parameter": f.parameter,
                                    "payload": f.payload,
                                    "response_snippet": (f.response_raw or "")[:500]
                                 }
                                 # Enhanced LLM reporting
                                 report = await self.llm_engine.analyze_and_score_finding(finding_data)
                                 
                                 return Finding(
                                    target_id=target.id,
                                    scan_id=self.scan_id,
                                    module_id=f.module_id,
                                    vuln_class=f.vuln_class,
                                    severity=report.get("severity", f.severity),
                                    cvss_score=report.get("cvss_score", ai_result["cvss_score"]),
                                    endpoint_url=f.endpoint,
                                    method=f.method,
                                    parameter=f.parameter,
                                    confidence=int(ai_result["confidence"] * 100),
                                    ai_summary=f"{report.get('executive_summary', '')}\n\n{report.get('technical_analysis', '')}",
                                    remediation=report.get("remediation_guidance", ""),
                                    request_raw=f.request_raw,
                                    response_raw=f.response_raw,
                                    status="NEW"
                                 )
                        except Exception as e:
                            logger.error(f"[AI] Error synthesizing finding: {e}")
                        return None

                    analysis_tasks = [process_finding(f) for f in active_findings]
                    processed_findings = await asyncio.gather(*analysis_tasks)
                    
                    for df in processed_findings:
                        if df: db.add(df)
                    await db.commit()

                # Completion
                scan.status = ScanStatus.COMPLETED
                scan.end_time = datetime.utcnow()
                await db.commit()
                
                await self._publish_live_stream("COMPLETED", f"Full Pentest Cycle Completed. Wrote {len([f for f in active_findings if f])} vulnerabilities.")

            except Exception as e:
                logger.error(f"[ENGINE] Critical failure on scan {self.scan_id}: {str(e)}")
                await self._publish_live_stream("FAILED", f"Critical internal error: {str(e)}")
                try:
                    scan.status = ScanStatus.FAILED
                    await db.commit()
                except: pass
            finally:
                await self.redis_client.aclose()
