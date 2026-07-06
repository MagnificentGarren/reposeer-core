import os
import time
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
import chromadb
from google.genai import types
from storage.memory_ledger import get_historical_weaknesses
import json
import difflib
from storage.memory_ledger import log_completed_session

# Explicitly execute the environment variable loader
load_dotenv()

# -----------------------------------------------------------------
# Global Client Initialization (Fixes NameError)
# -----------------------------------------------------------------
ai_client = genai.Client()

# Define the shared communication state between our agents
class AgentState(TypedDict):
    query: str
    messages: List[Dict[str, str]]
    retrieved_code_vectors: List[Dict[str, Any]]
    repo_blueprint: Dict[str, Any]
    current_draft: str
    review_feedback: str
    steps_taken: List[str]
    # -----------------------------------------------------------------
    # Phase 4: Interview Simulation States
    # -----------------------------------------------------------------
    session_mode: str          # "casual" or "interview"
    difficulty: str            # "easy", "medium", "hard"
    interviewer_persona: str   # "collaborator", "traditionalist", "architect"
    current_question_index: int # Track which question we are on (1 to 5)
    evaluation_scores: List[Dict[str, Any]] # Store grades per turn

# -----------------------------------------------------------------
# Core Processing Nodes
# -----------------------------------------------------------------

def router_node(state: AgentState) -> Dict[str, Any]:
    print("🤖 Agent Node [Router]: Analyzing context and querying vector store...")
    
    # 1. Skip vector querying if initializing an exam session out of nothing
    if state["query"] == "INITIALIZE_INTERVIEW_SESSION":
        return {"retrieved_code_vectors": [], "steps_taken": state.get("steps_taken", []) + ["live_routed"]}

    search_query = state["query"]
    
    # If there is active conversation history, condense it into a standalone search term
    if state.get("messages") and len(state["messages"]) > 1:
        print("   ↳ 🧠 Context detected. Condensing shorthand query via Gemini...")
        
        chat_history_context = ""
        for msg in state["messages"][:-1]:
            chat_history_context += f"{msg['role']}: {msg['content']}\n"
            
        condensation_prompt = (
            f"Given the following conversation history and a new shorthand follow-up question, "
            f"rewrite the new question into a standalone, descriptive search query focused on resolving "
            f"the intended codebase target files or symbols.\n\n"
            f"Conversation History:\n{chat_history_context}\n"
            f"New Follow-up Question: {state['query']}\n\n"
            f"Output ONLY the optimized search string. Do not include introductory text."
        )
        
        try:
            condensation_response = ai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=condensation_prompt
            )
            optimized_query = condensation_response.text.strip()
            if optimized_query:
                search_query = optimized_query
                print(f"   ↳ Optimized Search Vector: '{search_query}'")
        except Exception as e:
            print(f"   ↳ ⚠️ Query condensation skipped due to error: {e}")

    # 2. Prefer using the active session blueprint if provided in state
    retrieved_docs = []
    blueprint = state.get("repo_blueprint") or {}

    # If blueprint is empty, attempt to load from disk using a thread id if present in state
    if not blueprint:
        thread_id = None
        # Attempt to find a thread id in state values
        thread_id = state.get("thread_id") or state.get("session_id")
        if not thread_id:
            # As a last resort, look for a configurable entry inside state if present
            config_block = state.get("configurable") if isinstance(state.get("configurable"), dict) else None
            if config_block:
                thread_id = config_block.get("thread_id")

        if thread_id:
            session_blueprint_file = os.path.join("storage", "blueprints", f"{thread_id}.json")
            if os.path.exists(session_blueprint_file):
                try:
                    with open(session_blueprint_file, "r", encoding="utf-8") as f:
                        blueprint = json.load(f)
                        print(f"   ↳ Loaded session blueprint from {session_blueprint_file}")
                except Exception as e:
                    print(f"   ↳ ⚠️ Failed to load blueprint file: {e}")

    # If we have a blueprint with mapped files, search within it for relevant symbols or functions
    if blueprint and isinstance(blueprint, dict) and blueprint.get("files"):
        files_map = blueprint.get("files", {})
        # Search for matching symbols in the mapped files
        for fname, meta in files_map.items():
            try:
                # Look for standalone functions and classes metadata
                funcs = meta.get("standalone_functions", []) if isinstance(meta, dict) else []
                classes = [c.get("name") for c in meta.get("classes", [])] if isinstance(meta, dict) else []

                matched = False
                # Build candidate symbol list and map back to original metadata
                candidate_map = {}
                candidate_names = []
                for fn in funcs:
                    name = fn.get("name") if isinstance(fn, dict) else (fn if isinstance(fn, str) else None)
                    if name:
                        candidate_map[name] = ("function", fn)
                        candidate_names.append(name)

                for cls in classes:
                    if cls:
                        candidate_map[cls] = ("class", cls)
                        candidate_names.append(cls)

                # Exact substring matches first
                for name in candidate_names:
                    if search_query.lower() in name.lower() or name.lower() in search_query.lower():
                        kind, payload = candidate_map[name]
                        if kind == "function":
                            fn = payload
                            retrieved_docs.append({
                                "file": meta.get("file_path", fname),
                                "scope": "function",
                                "symbol_name": fn.get("name") if isinstance(fn, dict) else fn,
                                "content": (fn.get("source_code") if isinstance(fn, dict) else "") or json.dumps(fn)
                            })
                        else:
                            retrieved_docs.append({
                                "file": meta.get("file_path", fname),
                                "scope": "class",
                                "symbol_name": name,
                                "content": json.dumps(meta.get("classes", []))
                            })
                        matched = True

                # If no substring matches, try fuzzy matching using difflib
                if not matched and candidate_names:
                    close = difflib.get_close_matches(search_query, candidate_names, n=3, cutoff=0.6)
                    for cname in close:
                        kind, payload = candidate_map.get(cname, (None, None))
                        if kind == "function":
                            fn = payload
                            retrieved_docs.append({
                                "file": meta.get("file_path", fname),
                                "scope": "function",
                                "symbol_name": fn.get("name") if isinstance(fn, dict) else fn,
                                "content": (fn.get("source_code") if isinstance(fn, dict) else "") or json.dumps(fn)
                            })
                        elif kind == "class":
                            retrieved_docs.append({
                                "file": meta.get("file_path", fname),
                                "scope": "class",
                                "symbol_name": cname,
                                "content": json.dumps(meta.get("classes", []))
                            })
                    if close:
                        matched = True

                # If no direct symbol matches but the blueprint contains source text, include a lightweight snippet
                if not matched and isinstance(meta, dict):
                    snippet = ""
                    if meta.get("standalone_functions"):
                        snippet = json.dumps(meta.get("standalone_functions")[:1])
                    elif meta.get("classes"):
                        snippet = json.dumps(meta.get("classes")[:1])

                    if snippet:
                        retrieved_docs.append({
                            "file": meta.get("file_path", fname),
                            "scope": "module",
                            "symbol_name": fname,
                            "content": snippet
                        })
            except Exception as e:
                print(f"   ↳ Error extracting from blueprint file {fname}: {e}")

        if retrieved_docs:
            print(f"   ↳ Retrieved {len(retrieved_docs)} docs from session blueprint map.")
            return {
                "retrieved_code_vectors": retrieved_docs,
                "steps_taken": state.get("steps_taken", []) + ["live_routed"]
            }

    # 3. Fallback: Query persistent storage collection (vector DB)
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db_data")
        collection = chroma_client.get_collection(name="repository_methods")

        results = collection.query(
            query_texts=[search_query],
            n_results=2
        )

        if results and results.get("documents") and results["documents"][0]:
            for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
                retrieved_docs.append({
                    "file": metadata.get("file_path", "unknown"),
                    "scope": metadata.get("scope", "unknown"),
                    "symbol_name": metadata.get("symbol_name", "unknown"),
                    "content": doc
                })
                print(f"   ↳ Extracted relevant {metadata.get('scope')}: '{metadata.get('symbol_name')}' from {metadata.get('file_path')}")
    except Exception as e:
        print(f"   ↳ ⚠️ Vector DB query failed: {e}")

    if not retrieved_docs:
        print("   ↳ ⚠️ Warning: No relevant code vectors found for this query.")

    return {
        "retrieved_code_vectors": retrieved_docs,
        "steps_taken": state.get("steps_taken", []) + ["live_routed"]
    }


def doc_agent_node(state: AgentState) -> Dict[str, Any]:
    print("📝 Agent Node [Doc Writer]: Generating production response via Gemini...")
    
    code_context = ""
    for vec in state.get("retrieved_code_vectors", []):
        code_context += f"\n--- FILE: {vec.get('file', 'unknown')} ({vec.get('scope', 'unknown')}: {vec.get('symbol_name', 'unknown')}) ---\n{vec.get('content', '')}\n"
    
    blueprint = state.get("repo_blueprint", {}) or {}
    blueprint_summary = ""
    if blueprint and isinstance(blueprint, dict) and blueprint.get("files"):
        summary_lines = []
        for file_name, metadata in list(blueprint["files"].items())[:5]:
            classes = [c.get("name") for c in metadata.get("classes", [])] if isinstance(metadata.get("classes"), list) else []
            funcs = [f.get("name") for f in metadata.get("standalone_functions", []) if isinstance(f, dict)] if isinstance(metadata.get("standalone_functions"), list) else []
            summary_lines.append(f"{file_name}: classes={classes}, functions={funcs}")
        blueprint_summary = "\n".join(summary_lines)
    
    chat_history_context = ""
    for msg in state.get("messages", []):
        chat_history_context += f"👤 {msg['role'].capitalize()}: {msg['content']}\n"
    
    system_instruction = (
        "You are an expert technical AI assistant linked directly to a local codebase. "
        "Your job is to provide clean, technical, and accurate code summaries or answers using the "
        "retrieved code context assets and conversation history. Always format code references within "
        "proper markdown ticks. "
        "If retrieved code context is available, prioritize it above generic guidance. "
        "If no retrieved vectors are present, fall back to the repository blueprint summary to ground your answer."
    )
    
    user_prompt = ""
    if chat_history_context:
        user_prompt += f"Prior Conversation History:\n{chat_history_context}\n"
    
    if code_context:
        user_prompt += f"Code Context Assets for Current Turn:\n{code_context}\n\n"
    elif blueprint_summary:
        user_prompt += f"Repository Blueprint Summary:\n{blueprint_summary}\n\n"
    else:
        user_prompt += "No direct code context was retrieved for this turn. Use the repository blueprint if available and answer as accurately as possible.\n\n"

    user_prompt += f"Latest User Query: {state['query']}"
    
    if state.get("review_feedback"):
        user_prompt += f"\n\nCRITICAL - Previous Review Feedback to Correct:\n{state['review_feedback']}"

    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config={"system_instruction": system_instruction}
    )
    
    step_tag = "documented_fixed" if state.get("review_feedback") else "documented_initial"
    
    return {
        "current_draft": response.text,
        "review_feedback": "",
        "steps_taken": state.get("steps_taken", []) + [step_tag]
    }




def reviewer_node(state: AgentState) -> Dict[str, Any]:
    steps = state.get("steps_taken", [])
    
    # -----------------------------------------------------------------
    # Live Structured Interview Evaluation Engine
    # -----------------------------------------------------------------
    if state.get("session_mode") == "interview":
        if state["query"] == "INITIALIZE_INTERVIEW_SESSION":
            return {"steps_taken": steps + ["interview_init_passed"]}
            
        print(f"🔬 Agent Node [Evaluator]: Structured grading for Question {state['current_question_index'] - 1}...")
        
        # Define a rigid JSON schema format matching your Knowledge Map design
        eval_schema = types.Schema(
            type=types.Type.OBJECT,
            properties={
                "score": types.Schema(type=types.Type.INTEGER, description="Grade from 0 to 10"),
                "critique": types.Schema(type=types.Type.STRING, description="Actionable 1-2 sentence technical review."),
                "architecture_percentage": types.Schema(type=types.Type.INTEGER, description="0-100 evaluation of architectural awareness."),
                "backend_logic_percentage": types.Schema(type=types.Type.INTEGER, description="0-100 evaluation of code and logic mechanics."),
                "security_percentage": types.Schema(type=types.Type.INTEGER, description="0-100 evaluation of vulnerabilities and bounds."),
                "databases_percentage": types.Schema(type=types.Type.INTEGER, description="0-100 evaluation of indexing, schemas, or data flow."),
                "scalability_percentage": types.Schema(type=types.Type.INTEGER, description="0-100 evaluation of scale, Big-O, or performance trade-offs."),
                "flagged_weaknesses": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(type=types.Type.STRING),
                    description="Lowercase concept tags candidate missed (e.g., 'indexes', 'redis caching', 'rate limiting'). Max 2."
                )
            },
            required=[
                "score", "critique", "architecture_percentage", "backend_logic_percentage", 
                "security_percentage", "databases_percentage", "scalability_percentage", "flagged_weaknesses"
            ]
        )

        # Pull the last question asked from memory history
        last_question = "Unknown context"
        for msg in reversed(state.get("messages", [])):
            if msg["role"] == "assistant":
                last_question = msg["content"]
                break
                
        user_prompt = f"Question Asked: {last_question}\nCandidate's Answer: {state['query']}"
        
        fallback_eval_data = {
            "score": 5,
            "critique": "Evaluation model temporarily rate-limited. Progress preserved.",
            "architecture_percentage": 50,
            "backend_logic_percentage": 50,
            "security_percentage": 50,
            "databases_percentage": 50,
            "scalability_percentage": 50,
            "flagged_weaknesses": []
        }

        eval_data = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                eval_response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=(
                            "You are an elite corporate technical evaluation board. Evaluate the candidate's answer "
                            "against professional standards. Grade out of 10 and map performance directly to the "
                            "individual technical category percentages."
                        ),
                        response_mime_type="application/json",
                        response_schema=eval_schema
                    )
                )
                eval_data = json.loads(eval_response.text)
                break
            except (APIError, Exception) as e:
                print(f"  ⚠️ Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print("  ❌ Max retries reached. Injecting safe default telemetry baseline.")
                    eval_data = fallback_eval_data

        if eval_data is None:
            eval_data = fallback_eval_data

        # Re-format text output for terminal printing display comfort
        raw_evaluation_output = (
            f"SCORE: {eval_data['score']}/10\n"
            f"CRITIQUE: {eval_data['critique']}\n"
            f"📊 CATEGORY BREAKDOWN:\n"
            f"  • Architecture:  {eval_data['architecture_percentage']}%\n"
            f"  • Backend Logic: {eval_data['backend_logic_percentage']}%\n"
            f"  • Security:      {eval_data['security_percentage']}%\n"
            f"  • Databases:     {eval_data['databases_percentage']}%\n"
            f"  • Scalability:   {eval_data['scalability_percentage']}%"
        )

        new_scores = state.get("evaluation_scores", []) + [{
            "question_num": state['current_question_index'] - 1,
            "raw_evaluation": raw_evaluation_output,
            "score": f"{eval_data['score']}/10",
            "json_payload": eval_data  # Pass along the raw values for the interface to catch
        }]
        
        return {
            "evaluation_scores": new_scores,
            "steps_taken": steps + ["interview_graded"]
        }

    print("🔬 Agent Node [Reviewer]: Evaluating documentation via Gemini QC...")


def interviewer_agent_node(state: AgentState) -> Dict[str, Any]:
    print(f"🎙️  Agent Node [Interviewer - Persona: {state['interviewer_persona'].upper()}]: Framing interview context...")
    
    # 1. Pull past weaknesses from the database
    historical_gaps = get_historical_weaknesses(limit=3)
    gap_instruction = ""
    if historical_gaps:
        gap_tags = [item["topic"] for item in historical_gaps]
        gap_instruction = f"\nCRITICAL ADAPTIVE BIAS: The candidate has historically struggled with: {', '.join(gap_tags)}. Subtlely target these domains."

    # 2. Extract structural hints out of our repository blueprint graph map
    blueprint = state.get("repo_blueprint", {})
    structural_context = ""
    if blueprint and "modules" in blueprint:
        # Provide a high-level summary list of actual project files and symbols to the LLM context window
        module_summary = []
        for mod, details in list(blueprint["modules"].items())[:8]:  # Keep context window clean
            classes = list(details.get("classes", {}).keys())
            funcs = details.get("standalone_functions", [])
            module_summary.append(f"Module '{mod}' contains Classes: {classes}, Standalone Functions: {funcs}")
        
        structural_context = (
            f"\nACTUAL REPOSITORY ARCHITECTURE STRUCTURE:\n"
            f"{chr(10).join(module_summary)}\n"
            f"Formulate questions that challenge the candidate to explain how these modules connect, "
            f"their design patterns (e.g., repository patterns, state machines), or architectural trade-offs."
        )

    active_context_pool = state.get("retrieved_code_vectors", []) or []
    workspace_name = os.path.basename(blueprint.get("repo_path", "AssetCitadel")) if isinstance(blueprint, dict) else "AssetCitadel"
    context_str = ""
    for doc in active_context_pool:
        if doc.get("content"):
            context_str += (
                f"\nEntity: {doc.get('symbol_name', 'unknown')}\n"
                f"File: {doc.get('file', 'unknown')}\n"
                f"Scope: {doc.get('scope', 'unknown')}\n"
                f"Source:\n{doc.get('content')}\n"
                f"---\n"
            )

    persona_prompts = {
        "collaborator": "You are 'The Helpful Collaborator', a friendly pair-programmer. Guide the candidate gently, give conceptual hints, and treat this like a team project.",
        "traditionalist": "You are 'The Strict Traditionalist', an algorithm purist. Speak concisely, stay cold, and focus heavily on raw syntax rules, decoupling mechanics, and optimal design patterns.",
        "architect": "You are 'The Pragmatic Architect', a production startup tech lead. Focus strictly on real-world constraints, scalability bottlenecks, deployment friction, and operational safety."
    }

    base_persona = persona_prompts.get(state["interviewer_persona"], "You are an expert technical interviewer.")
    
    if context_str:
        system_instruction = (
            f"{base_persona}\n"
            f"Target Workspace Mounted: {workspace_name}\n"
            f"Your target difficulty level is set to: {state['difficulty'].upper()}.\n"
            f"CRITICAL INSTRUCTION: You are strictly evaluating the user's live code base configuration.\n"
            f"Do NOT ask generic questions about microservices or crypto utilities. Instead, analyze the specific code implementations provided below.\n"
            f"Challenge the user on their validation boundaries, optimization vectors, or edge-case handling within these actual functions.\n\n"
            f"---\n"
            f"MOUNTED BASELINE IMPLEMENTATIONS:\n"
            f"{context_str}"
            f"---\n"
            f"Formulate your technical question directly targeting specific components found above."
        )
        mock_trigger_prompt = (
            f"Generate interview question #{state['current_question_index']} based on the mounted code context and actual extracted implementations."
        )
    else:
        system_instruction = (
            f"{base_persona}\n"
            f"Your target difficulty level is set to: {state['difficulty'].upper()}.\n"
            f"Your goal is to formulate and output ONLY the text for Question #{state['current_question_index']} of 5 "
            f"testing the candidate's understanding of their specific repository architecture.{gap_instruction}{structural_context}\n"
            f"Do not include grading metrics or conversational meta-commentary."
        )
        mock_trigger_prompt = f"Generate interview question #{state['current_question_index']} based on the verified structural project context."
    
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=mock_trigger_prompt,
        config={"system_instruction": system_instruction}
    )
    
    return {
        "current_draft": response.text,
        "steps_taken": state.get("steps_taken", []) + ["interviewer_question_generated"]
    }

# =====================================================================
# Optimized LangGraph Routing & Conversation State Machine
# =====================================================================

def mode_router(state: AgentState) -> str:
    """
    Directs the initial routing track.
    """
    # If it's an interview session, let the evaluation router determine the node path
    if state.get("session_mode") == "interview":
        # First turn initialization bypasses grading
        if "INITIALIZE_INTERVIEW_SESSION" in state["query"] or state.get("current_question_index", 1) == 1:
            return "generate_interview_turn"
        return "evaluate_quality"
        
    return "write_docs"

def post_evaluation_router(state: AgentState) -> str:
    """
    Determines where to route after an evaluation node finishes processing.
    """
    if state.get("session_mode") == "interview":
        # If the candidate has not finished all 5 questions, loop back to generate the next question
        if state.get("current_question_index", 1) <= 5:
            return "generate_interview_turn"
        else:
            # Session complete! Build the metadata and summary scores expected by the ledger
            evaluation_scores = state.get("evaluation_scores", [])
            category_scores = {
                "architecture": 50.0,
                "backend_logic": 50.0,
                "security": 50.0,
                "databases": 50.0,
                "scalability": 50.0
            }
            weaknesses = []
            count = 0

            for entry in evaluation_scores:
                payload = entry.get("json_payload") or {}
                if payload:
                    count += 1
                    category_scores["architecture"] += payload.get("architecture_percentage", 50)
                    category_scores["backend_logic"] += payload.get("backend_logic_percentage", 50)
                    category_scores["security"] += payload.get("security_percentage", 50)
                    category_scores["databases"] += payload.get("databases_percentage", 50)
                    category_scores["scalability"] += payload.get("scalability_percentage", 50)
                    weaknesses.extend(payload.get("flagged_weaknesses", []))

            if count > 0:
                category_scores = {k: v / count for k, v in category_scores.items()}

            weaknesses = [w.strip().lower() for w in set(weaknesses) if w and isinstance(w, str)]

            metadata = {
                "session_mode": state.get("session_mode", "interview"),
                "difficulty": state.get("difficulty", "medium"),
                "interviewer_persona": state.get("interviewer_persona", "architect")
            }

            try:
                log_completed_session(metadata, category_scores, weaknesses)
            except Exception as log_error:
                print(f"  ⚠️ Failed to persist completed session: {log_error}")
            return "end"
            
    # Documentation QC loop logic falls back here
    if state.get("review_feedback"):
        return "write_docs"
    return "end"

# 1. Initialize the State Graph Blueprint
workflow = StateGraph(AgentState)

# 2. Register Processing Nodes
workflow.add_node("route_and_fetch", router_node)
workflow.add_node("write_docs", doc_agent_node)
workflow.add_node("evaluate_quality", reviewer_node)
workflow.add_node("generate_interview_turn", interviewer_agent_node)

# 3. Configure Edge Flows
workflow.set_entry_point("route_and_fetch")

# Route conditionally from start point
workflow.add_conditional_edges(
    "route_and_fetch",
    mode_router,
    {
        "write_docs": "write_docs",
        "generate_interview_turn": "generate_interview_turn",
        "evaluate_quality": "evaluate_quality"
    }
)

# Connect intermediate nodes to the evaluator
workflow.add_edge("write_docs", "evaluate_quality")

# In interview mode, once an evaluation turn completes, look ahead to determine if we loop or end
workflow.add_conditional_edges(
    "evaluate_quality",
    post_evaluation_router,
    {
        "generate_interview_turn": "generate_interview_turn",
        "write_docs": "write_docs",
        "end": END
    }
)

# Crucial fix: Once the interviewer node asks a question, wrap the state response turn back to the user
workflow.add_edge("generate_interview_turn", END)

# Initialize the checkpointer and compile the workflow with memory support
memory_checkpointer = MemorySaver()
orchestrator_app = workflow.compile(checkpointer=memory_checkpointer)