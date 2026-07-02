import os
import sys
import json
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Force Python to treat the root workspace directory as an accessible module package path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now safely import your compiled LangGraph instance from your script
from agents.orchestrator import orchestrator_app

app = FastAPI(title="Reposeer-Core Telemetry API")

# Enable CORS for Next.js workspace connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "reposeer_profile.db"
BLUEPRINT_PATH = "repo_blueprint.json"

class ChatMessage(BaseModel):
    message: str
    session_id: str = "default_session"

@app.get("/api/telemetry")
def get_telemetry_data():
    """Aggregates local database logs and code architecture blueprints."""
    response_data = {
        "blueprint": {},
        "metrics": {"Architecture": 0.0, "Backend Logic": 0.0, "Security": 0.0, "Databases": 0.0, "Scalability": 0.0},
        "weaknesses": []
    }

    if os.path.exists(BLUEPRINT_PATH):
        try:
            with open(BLUEPRINT_PATH, "r", encoding="utf-8") as f:
                response_data["blueprint"] = json.load(f)
        except Exception:
            pass

    if os.path.exists(DB_PATH):
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    AVG(architecture_score), AVG(backend_logic_score), 
                    AVG(security_score), AVG(database_score), AVG(scalability_score) 
                FROM session_metrics
            """)
            row = cursor.fetchone()
            if row and row[0] is not None:
                response_data["metrics"] = {
                    "Architecture": round(row[0], 1),
                    "Backend Logic": round(row[1], 1),
                    "Security": round(row[2], 1),
                    "Databases": round(row[3], 1),
                    "Scalability": round(row[4], 1)
                }
            cursor.execute("SELECT DISTINCT topic_tag FROM concept_weaknesses")
            response_data["weaknesses"] = [tag[0] for tag in cursor.fetchall()]
            conn.close()
        except Exception:
            pass

    return response_data

@app.post("/api/chat/submit")
def submit_chat_turn(payload: ChatMessage):
    user_input = payload.message.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Input cannot be empty.")

    try:
        repo_blueprint_data = {}
        if os.path.exists(BLUEPRINT_PATH):
            with open(BLUEPRINT_PATH, "r", encoding="utf-8") as f:
                repo_blueprint_data = json.load(f)

        # Extract the dynamic client-side message counter from session_id
        try:
            history_length = int(payload.session_id)
        except ValueError:
            history_length = 1

        # Calculate exactly where we are in the 5-question interview loop
        # History length of 1 means only the initial greeting is present -> Next is Question 1
        if history_length <= 1:
            active_question_index = 1
        else:
            # Every conversation round consists of 2 messages (User response + Agent question).
            # This cleanly increments your question tracking pointer automatically.
            active_question_index = (history_length // 2) + 1

        print(f"📡 Incoming Payload Turn Calculation -> Chat History Length: {history_length} | Assigned Question Index: {active_question_index}")

        inputs = {
            "query": user_input,
            "messages": [{"role": "user", "content": user_input}],
            "retrieved_code_vectors": [],
            "repo_blueprint": repo_blueprint_data,
            "current_draft": "",
            "review_feedback": "",
            "steps_taken": [],
            "session_mode": "interview",
            "difficulty": "medium",
            "interviewer_persona": "architect",
            "current_question_index": active_question_index, # ◄── Perfectly tracked turn pointer
            "evaluation_scores": []
        }

        final_output = orchestrator_app.invoke(inputs)

        # Check if we just completed the final question
        if active_question_index >= 6:
            agent_reply = (
                "### 🎓 Interview Session Complete!\n\n"
                "Thank you for completing the Reposeer Core architectural evaluation. "
                "Your responses have been compiled, graded, and synced to your local telemetry ledger. "
                "You can now view your updated competency metrics matrix in the sidebar panel."
            )
        else:
            agent_reply = final_output.get("current_draft") or "Next question initializing..."

        return {"status": "success", "reply": agent_reply}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph Engine Error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)