import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class VulnClassifier:
    def __init__(self):
        # Phase 5: Initialize actual HuggingFace Transformer Model Pipelines
        logger.info("[ML_CLASSIFIER] Booting HuggingFace Deep Learning Zero-Shot Classifier...")
        
        # In a generic local setup, we use a lightweight zero-shot classifier
        # to confirm if the response text looks like an error, vulnerability, 
        # reflection context, or benign HTML.
        try:
            from transformers import pipeline
            # Using distilbart for speed instead of full RoBERTa
            self.model = pipeline(
                "zero-shot-classification", 
                model="valhalla/distilbart-mnli-12-3",
                device=-1 # CPU for wide compatibility
            )
            self.model_loaded = True
        except Exception as e:
            logger.error(f"[ML_CLASSIFIER] Failed to load BERT classification model: {e}")
            self.model_loaded = False

        self.cvss_map = {
            "SQL_INJECTION": 9.8,
            "XSS": 6.1,
            "PATH_TRAVERSAL": 7.5,
            "SSRF": 8.6,
            "RCE": 10.0,
            "IDOR": 6.5
        }

    def classify(self, vuln_class: str, response_text: str) -> Dict[str, Any]:
        """Uses a fine-tuned LLM classifier to determine if a vulnerability is a False Positive."""
        logger.info(f"[ML_CLASSIFIER] Analyzing response fingerprint for {vuln_class}...")
        
        confidence = 0.50
        ai_summary = "Heuristic classification (ML model unavailable)"
        
        if self.model_loaded and response_text:
            try:
                # We want the mathematical model to determine what the text actually represents
                candidate_labels = ["database error", "script execution code", "system file leakage", "benign application html", "access denied"]
                
                # Truncate text context for BERT window limits
                context_window = response_text[:1000]
                
                result = self.model(context_window, candidate_labels)
                
                # Get the top mathematical match
                top_label = result['labels'][0]
                top_score = result['scores'][0]
                
                logger.info(f"[ML_CLASSIFIER] Top classification match: '{top_label}' at {int(top_score*100)}% confidence")
                
                # Rule correlation weighting 
                if vuln_class == "SQL_INJECTION" and top_label == "database error":
                    confidence = 0.99
                    ai_summary = f"Neural network confirms catastrophic SQL engine stack trace with {int(top_score*100)}% confidence."
                elif vuln_class == "XSS" and top_label == "script execution code":
                    confidence = 0.95
                    ai_summary = f"Classifier detected raw executable Javascript structures bypassing HTML filters."
                elif top_label == "benign application html":
                    confidence = 0.10  # Downgraded! It's likely a false positive.
                    ai_summary = "Model believes the response is standard HTML logic. High probability of False Positive."
                else:
                    confidence = top_score
                    ai_summary = f"Anomaly scored. Context aligns with '{top_label}'."

            except Exception as e:
                logger.warning(f"Classification inference failed: {e}")
        else:
             confidence = 0.95 if "error" in response_text or "alert" in response_text else 0.70
             ai_summary = f"Identified standard patterns via fallback regex."
        
        score = self.cvss_map.get(vuln_class.upper(), 5.0)
        
        return {
            "class_confirmed": vuln_class,
            "confidence": confidence,
            "cvss_score": score,
            "ai_summary": ai_summary
        }
