import os
import sys
import json
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from analyzer.crawler import crawl_repository
from analyzer.vector_store import store_codebase_vectors

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

class RepoSelectPayload(BaseModel):
    repo_path: str
    session_id: str

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

@app.post("/api/repo/select")
def select_and_scan_repository(payload: RepoSelectPayload):
    target_path = payload.repo_path.strip()

    if not os.path.exists(target_path):
        raise HTTPException(
            status_code=400,
            detail=f"Target path layout not found on this system: '{target_path}'"
        )

    try:
        print(f"📁 Initializing deep AST crawl on target workspace: {target_path}")

        # 2. Trigger your crawler logic directly
        parsed_list = crawl_repository(target_path)

        # 🌟 WRAP the flat array into a standardized blueprint dictionary schema
        blueprint_data = {
            "repo_path": target_path,
            # Use module-relative paths as keys when present to avoid basename collisions
            "files": {
                (item.get("module") or os.path.basename(item.get("file_path", "module"))): item
                for item in parsed_list if isinstance(item, dict)
            } if parsed_list and isinstance(parsed_list[0], dict) else {},
            "raw_ast_pool": parsed_list
        }

        # 3. Cache the structured blueprint to disk
        session_blueprint_dir = os.path.join("storage", "blueprints")
        os.makedirs(session_blueprint_dir, exist_ok=True)

        target_blueprint_file = os.path.join(session_blueprint_dir, f"{payload.session_id}.json")
        with open(target_blueprint_file, "w", encoding="utf-8") as f:
            json.dump(blueprint_data, f, indent=4)
        # Attempt to seed the vector DB with extracted code vectors for faster retrieval
        try:
            store_codebase_vectors(parsed_list)
        except Exception as e:
            print(f"   ↳ ⚠️ Seeding vector DB failed: {e}")
            
        print(f"💾 Ingestion complete. Balanced blueprint schema written!")
        
        return {
            "status": "success",
            "message": f"Successfully indexed workspace data at {target_path}",
            "file_count": len(parsed_list) if isinstance(parsed_list, list) else 0
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AST Ingestion Pipeline failed: {str(e)}"
        )

@app.post("/api/chat/submit")
def submit_chat_turn(payload: ChatMessage):
    user_input = payload.message.strip()
    if not user_input:
        raise HTTPException(status_code=400, detail="Input cannot be empty.")

    try:
        # 🧠 USE AN EXPLICIT SESSION THREAD FOR CHECKPOINTING
        thread_id = payload.session_id if payload.session_id else "default_session"
        session_blueprint_file = os.path.join("storage", "blueprints", f"{thread_id}.json")

        repo_blueprint_data = {}
        if os.path.exists(session_blueprint_file):
            with open(session_blueprint_file, "r", encoding="utf-8") as f:
                repo_blueprint_data = json.load(f)
        else:
            if os.path.exists(BLUEPRINT_PATH):
                with open(BLUEPRINT_PATH, "r", encoding="utf-8") as f:
                    repo_blueprint_data = json.load(f)
        config = {"configurable": {"thread_id": thread_id}}

        current_state = orchestrator_app.get_state(config)
        if not current_state.values:
            active_question_index = 1
        else:
            last_index = current_state.values.get("current_question_index", 1)
            active_question_index = last_index + 1

        print(f"📡 Checkpointer Thread: {thread_id} | Resolved Internal State Question Index: {active_question_index}")

        inputs = {
            "query": user_input,
            "messages": [{"role": "user", "content": user_input}],
            "retrieved_code_vectors": [],
            "repo_blueprint": repo_blueprint_data,
            "session_mode": "interview",
            "difficulty": "medium",
            "interviewer_persona": "architect",
            "current_question_index": active_question_index,
        }

        final_output = orchestrator_app.invoke(inputs, config=config)

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


@app.get("/api/blueprint/{session_id}")
def get_session_blueprint(session_id: str):
    session_blueprint_file = os.path.join("storage", "blueprints", f"{session_id}.json")
    if not os.path.exists(session_blueprint_file):
        raise HTTPException(status_code=404, detail="Blueprint not found for given session_id")
    try:
        with open(session_blueprint_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load blueprint: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)