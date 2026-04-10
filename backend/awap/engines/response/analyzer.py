import logging
import httpx
from typing import Dict, Any
from sklearn.ensemble import IsolationForest
import numpy as np

logger = logging.getLogger(__name__)

class ResponseAnalysisEngine:
    def __init__(self):
        # We use an IsolationForest to detect statistical anomalies in response properties
        # (Content-Length, Response-Time, Headers-Count, Status-Code changes)
        self.anomaly_detector = IsolationForest(contamination=0.01, random_state=42)
        self.baselines = {}
        
        # Standard error signatures indicating successful command execution, syntax failure, or internal leaks
        self.error_signatures = [
            "SQL syntax", "mysql_fetch_array", "ORA-01756", "PostgreSQL query failed",
            "java.lang.NullPointerException", "IndexOutOfBoundsException", "Fatal error:",
            "Traceback (most recent call last):", "SyntaxError:", "mysql_connect()",
            "root:x:0:0:root", "www-data", "[boot loader]", "/bin/bash"
        ]

    def build_baseline(self, endpoint_url: str, baseline_responses: list[httpx.Response]):
        """
        Creates a statistical baseline of 'normal' traffic for an endpoint so we can 
        detect differential anomalies later (blind SQLi, behavior shifts).
        """
        logger.info(f"[RAE] Building statistical baseline for {endpoint_url}")
        
        if not baseline_responses:
            return
            
        # Extract features: [status_code, length, response_time_ms]
        features = [
            [resp.status_code, len(resp.content), resp.elapsed.total_seconds() * 1000] 
            for resp in baseline_responses
        ]
        
        # Fit the Isolation Forest to the 'normal' distribution
        X = np.array(features)
        
        # For very small standard deviation (all responses exactly the same), 
        # we add tiny jitter to prevent singular matrix errors in IsolationForest
        jitter = np.random.normal(0, 0.001, X.shape)
        X = X + jitter
        
        model = IsolationForest(contamination=0.05, random_state=42)
        model.fit(X)
        
        self.baselines[endpoint_url] = {
            "model": model,
            "mean_length": np.mean(X[:, 1]),
            "mean_time": np.mean(X[:, 2])
        }

    def analyze_response(self, endpoint_url: str, response: httpx.Response, payload: str) -> Dict[str, Any]:
        """
        Analyzes a single attack response against both signature logic and statistical baselines.
        Returns a dict containing detection confidence and evidence.
        """
        result: Dict[str, Any] = {
            "is_vulnerable": False,
            "confidence": 0.0,
            "evidence": []
        }
        
        content_str = response.text.lower()
        
        # 1. Reflection Detection (For XSS)
        if payload.lower() in content_str:
            result["evidence"].append("DIRECT_REFLECTION_FOUND")
            # Calculate context confidence based on whether it escaped tags
            if '"><' in payload or "'>" in payload:
                result["confidence"] += 0.4
            else:
                result["confidence"] += 0.2

        # 2. Syntax/Error Pattern Recognition (For Backend Injection)
        for sig in self.error_signatures:
            if sig.lower() in content_str:
                result["evidence"].append(f"ERROR_SIGNATURE_MATCH: {sig}")
                result["confidence"] += 0.8
                break

        # 3. Statistical Anomaly Detection (Blind/Differential vulnerabilities)
        baseline = self.baselines.get(endpoint_url)
        if baseline:
            test_features = np.array([[
                response.status_code, 
                len(response.content), 
                response.elapsed.total_seconds() * 1000
            ]])
            
            # Predict returns -1 for inliers (normal) and 1 for outliers (anomalies) in our modified setup
            prediction = baseline["model"].predict(test_features)
            
            # Since IsolationForest returns -1 for outlier natively, we check for -1
            if prediction[0] == -1:
                # Calculate exactly why it deviated explicitly
                len_diff = abs(len(response.content) - baseline["mean_length"])
                time_diff = abs((response.elapsed.total_seconds() * 1000) - baseline["mean_time"])
                
                if time_diff > 2000: # Time-based blindness > 2s deviation
                    result["evidence"].append(f"TIME_ANOMALY: +{int(time_diff)}ms delay detected")
                    result["confidence"] += 0.95
                elif len_diff > 500: # Length-based blindness > 500 byte deviation
                    result["evidence"].append(f"LENGTH_ANOMALY: {int(len_diff)} byte variance")
                    result["confidence"] += 0.6

        # If confidence crosses threshold, it's flagged
        if result["confidence"] >= 0.5:
            result["is_vulnerable"] = True
            
        return result
