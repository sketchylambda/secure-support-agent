import time
import logging
import hashlib
from collections import defaultdict
from datetime import datetime, timedelta
from google.adk.plugins import base_plugin
from google.genai import types
from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
import traceback

# For Privacy-Preserving Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("safety_auditor")

# User Feedback Loop message
FEEDBACK_MSG = "\n\nIf you believe this was a mistake, you can:\n1. Rephrase your question\n2. Report a false positive: https://support.example.com/ai-feedback"

class SafetyMetricsPlugin(base_plugin.BasePlugin):
    """Tracks safety events, logs hashes, and triggers alerts."""
    def __init__(self):
        super().__init__(name="safety_metrics")
        self.metrics = {
            "total_messages": 0,
            "blocked_messages": 0,
            "blocks_by_reason": defaultdict(int),
            "blocks_by_user": defaultdict(int),
            "pii_redactions": 0
        }

    async def on_user_message_callback(self, invocation_context, user_message) -> None:
        self.metrics["total_messages"] += 1

    def record_block(self, reason: str, user_id: str, message_text: str):
        # Privacy-Preserving Logging 
        msg_hash = hashlib.sha256(message_text.encode()).hexdigest()
        logger.warning(f"Blocked attempt | Hash: {msg_hash} | Reason: {reason} | User: {user_id}")
        
        self.metrics["blocked_messages"] += 1
        self.metrics["blocks_by_reason"][reason] += 1
        self.metrics["blocks_by_user"][user_id] += 1
        
        # Monitor and Alert
        if self.metrics["blocks_by_user"][user_id] >= 5:
            logger.critical(f"🚨 SECURITY ALERT: User {user_id} exceeded block threshold (5+ blocks). Triggering SOC review.")

    def record_redaction(self):
        self.metrics["pii_redactions"] += 1

class RateLimitPlugin(base_plugin.BasePlugin):
    """Prevents abuse by limiting how many messages a user can send per minute."""
    
    # Pass in the metrics_plugin so the rate limiter can report blocks
    def __init__(self, metrics_plugin, max_messages_per_minute: int = 5):
        super().__init__(name="rate_limit")
        self.metrics = metrics_plugin
        self.max_messages_per_minute = max_messages_per_minute
        self.user_message_timestamps = defaultdict(list)

    async def on_user_message_callback(self, invocation_context, user_message) -> types.Content | None:
        if not invocation_context.session.state.get("is_safe", True): return None
        
        user_id = invocation_context.session.user_id
        text = user_message.parts[0].text
        
        current_time = time.time()
        
        # Clean up messages older than 1 min
        self.user_message_timestamps[user_id] = [
            t for t in self.user_message_timestamps[user_id] 
            if current_time - t < 60
        ]
        
        if len(self.user_message_timestamps[user_id]) >= self.max_messages_per_minute:
            # Pass all 3 arguments to record_block
            self.metrics.record_block("Rate Limit Exceeded", user_id, text)
            invocation_context.session.state["is_safe"] = False
            raise PermissionError("[RATE LIMITED] You are sending messages too quickly.")
            
        self.user_message_timestamps[user_id].append(current_time)
        return None

class BannedWordsPlugin(base_plugin.BasePlugin):
    """Fast baseline filtering for deterministic bad words."""
    
    def __init__(self, metrics_plugin, banned_words: list[str] = None):
        super().__init__(name="banned_words")
        self.metrics = metrics_plugin
        self.banned_words = banned_words or ["hack", "ignore instructions", "bypass"]

    async def on_user_message_callback(self, invocation_context, user_message) -> types.Content | None:
        if not invocation_context.session.state.get("is_safe", True): return None
        
        text = user_message.parts[0].text
        user_id = invocation_context.session.user_id  
        
        for word in self.banned_words:
            if word.lower() in text.lower():
                # Pass all 3 arguments to record_block
                self.metrics.record_block(f"Banned Word Detected ({word})", user_id, text)
                invocation_context.session.state["is_safe"] = False
                raise PermissionError("[BANNED WORD DETECTED] Request blocked by security policies.")
                
        return None

class MultilingualJudgePlugin(base_plugin.BasePlugin):
    """Context-aware safety judge with Graceful Degradation."""
    def __init__(self, judge_agent, metrics_plugin: SafetyMetricsPlugin):
        super().__init__(name="multilingual_judge")
        self.judge_agent = judge_agent
        self.metrics = metrics_plugin
        from google.adk import runners
        self.judge_runner = runners.InMemoryRunner(agent=judge_agent, app_name="judge")

    async def on_user_message_callback(self, invocation_context, user_message) -> types.Content | None:
        if not invocation_context.session.state.get("is_safe", True): return None
        
        text = user_message.parts[0].text
        user_id = invocation_context.session.user_id
        wrapped = f"<user_message>\n{text}\n</user_message>"
        msg = types.Content(role="user", parts=[types.Part.from_text(text=wrapped)])
        
        response_text = ""
        
        try:
            judge_session = await self.judge_runner.session_service.create_session(
                user_id="sys", 
                app_name="judge"
            )
            
            async for event in self.judge_runner.run_async(
                user_id="sys", 
                session_id=judge_session.id, 
                new_message=msg
            ):
                if event.is_final_response() and event.content:
                    response_text = event.content.parts[0].text or ""
                    break
                    
        except Exception as e:
            print("\n" + "="*50)
            print("🚨 JUDGE CRASH DETECTED 🚨")
            traceback.print_exc() 
            print("="*50 + "\n")
            
            error_details = repr(e)
            
            self.metrics.record_block("Safety Judge Timeout/Error", user_id, text)
            raise PermissionError(f"[SYSTEM ERROR - FAIL SAFE] Safety judge offline. Details: {error_details}")
            
        if "UNSAFE" in response_text.upper():
            self.metrics.record_block("Jailbreak / Unsafe Intent", user_id, text)
            raise PermissionError("[UNSAFE INTENT DETECTED] Malicious prompt blocked by LLM Judge.")
            
        return None
    
class PresidioDLPPlugin(base_plugin.BasePlugin):
    """Data Loss Prevention: Redacts PII from the agent's final output."""
    def __init__(self, metrics_plugin: SafetyMetricsPlugin):
        super().__init__(name="presidio_dlp")
        self.analyzer = AnalyzerEngine()
        self.anonymizer = AnonymizerEngine()
        self.metrics = metrics_plugin
        print("🔒 Presidio DLP Engine Initialized")

    async def after_model_callback(self, callback_context, llm_response):
        # Safety check
        if not llm_response or not getattr(llm_response, "content", None) or not llm_response.content.parts:
            return llm_response
            
        # Extract text by going through the .content attribute first
        text = llm_response.content.parts[0].text
        
        # If there is no text (it's a tool call), let it pass through unhindered!
        if not text:
            return llm_response
            
        # If there IS text, run the Presidio DLP scanner
        results = self.analyzer.analyze(
            text=text, 
            entities=["PERSON", "LOCATION", "PHONE_NUMBER", "EMAIL_ADDRESS"], 
            language='en'
        )
        
        if results:
            anonymized = self.anonymizer.anonymize(text=text, analyzer_results=results)
            # Re-assign the redacted text back into the correct deep hierarchy
            llm_response.content.parts[0].text = anonymized.text
            
            if hasattr(self, 'metrics'):
                self.metrics.record_redaction()
                
        return llm_response
