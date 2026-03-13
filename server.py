import os
import time
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
from google.genai import types

# ====================================================================
# 🔐 ENVIRONMENT SETUP
# ====================================================================
# Load variables from the .env file BEFORE importing the agent
load_dotenv()
if not os.environ.get("GEMINI_API_KEY"):
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

# ====================================================================
# 🧠 IMPORT AI ARCHITECTURE
# ====================================================================
# Import the exact runner and metrics plugin defined in agent.py
from src.agent import runner, metrics_plugin

app = FastAPI()

# --- 📁 Static File Configuration ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- 🗄️ SOC Telemetry Additions ---
threat_timeline = []
active_sessions = {}

class ChatRequest(BaseModel):
    session_id: str
    message: str

# ====================================================================
# 🌐 USER ROUTES
# ====================================================================
@app.get("/", response_class=HTMLResponse)
async def serve_chat():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    session_id = req.session_id
    user_msg = req.message
    
    # 1. Register new sessions dynamically with the ADK runner
    if session_id not in active_sessions:
        # Create an official ADK session state to maintain conversation memory
        adk_session = await runner.session_service.create_session(
            user_id=session_id, 
            app_name="secure_support"
        )
        active_sessions[session_id] = {
            "msg_count": 0, 
            "blocks": 0,
            "adk_session_id": adk_session.id
        }
    
    active_sessions[session_id]["msg_count"] += 1
    adk_session_id = active_sessions[session_id]["adk_session_id"]
    
    try:
        safe_response = ""

        formatted_message = types.Content(
            role="user", 
            parts=[types.Part.from_text(text=user_msg)]
        )
        
        # 2. THE REAL BRAIN: Run the ADK pipeline
        async for event in runner.run_async(
            user_id=session_id, 
            session_id=adk_session_id, 
            new_message=formatted_message
        ):
            if event.is_final_response() and event.content:
                safe_response = event.content.parts[0].text or ""

        return {"reply": safe_response}

    except PermissionError as e:
        # 3. CATCH SECURITY BLOCKS
        active_sessions[session_id]["blocks"] += 1
        threat_timeline.append(time.strftime("%H:%M:%S"))
        
        error_msg = str(e)
        clean_msg = error_msg.split("callback: ")[-1] if "callback: " in error_msg else error_msg
        
        # The false-positive feedback link
        feedback_url = "https://docs.google.com/forms/mock-feedback-link"
        feedback_html = f"<br><br><hr><p>📝 Think this was a mistake? <a href='{feedback_url}' target='_blank' style='color: var(--neon-cyan);'>Submit a Security Appeal</a></p>"
        
        return {"reply": f"🛡️ <strong>SECURITY INTERVENTION:</strong> {clean_msg}{feedback_html}"}
        
    except Exception as e:
        error_repr = str(e)
        # Fallback block catch in case ADK wraps the PermissionError
        if "UNSAFE" in error_repr or "BANNED" in error_repr or "RATE LIMITED" in error_repr:
            threat_timeline.append(time.strftime("%H:%M:%S"))
            feedback_html = "<br><br><hr><p>📝 Think this was a mistake? <a href='#' style='color: var(--neon-cyan);'>Submit a Security Appeal</a></p>"
            return {"reply": f"🛡️ <strong>SECURITY INTERVENTION:</strong> Prompt blocked by security policies.{feedback_html}"}
            
        return {"reply": f"⚠️ An unexpected system error occurred: {error_repr}"}

# ====================================================================
# 🔐 ADMIN ROUTES (SOC Dashboard)
# ====================================================================
@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    with open(os.path.join(STATIC_DIR, "admin.html"), "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/admin/metrics")
async def get_metrics():
    # Fetch live data directly from guardrails.py metrics plugin!
    raw_metrics = metrics_plugin.metrics
    
    # Map dynamic guardrail reasons to the specific Chart.js dashboard categories
    mapped_blocks = {
        "Prompt Injection": sum(v for k, v in raw_metrics["blocks_by_reason"].items() if "Jailbreak" in k or "Unsafe" in k),
        "Banned Words": sum(v for k, v in raw_metrics["blocks_by_reason"].items() if "Banned Word" in k),
        "Data Exfiltration": sum(v for k, v in raw_metrics["blocks_by_reason"].items() if "Exfiltration" in k)
    }
    
    return {
        "metrics": {
            "total_messages": raw_metrics["total_messages"],
            "blocked_messages": raw_metrics["blocked_messages"],
            "pii_redactions": raw_metrics["pii_redactions"],
            "blocks_by_reason": mapped_blocks,
            "threat_timeline": threat_timeline
        },
        "active_users": len(active_sessions),
        "session_data": active_sessions
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)