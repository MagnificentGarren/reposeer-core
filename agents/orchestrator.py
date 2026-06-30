import os
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from langgraph.graph import StateGraph, END
import chromadb
from google.genai import types
from storage.memory_ledger import get_historical_weaknesses
import json
from google.genai import types  # Ensure you import types at the top for schemas
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

    # 2. Query persistent storage collection
    chroma_client = chromadb.PersistentClient(path="./chroma_db_data")
    collection = chroma_client.get_collection(name="repository_methods")
    
    results = collection.query(
        query_texts=[search_query],
        n_results=2
    )
    
    retrieved_docs = []
    if results and results["documents"] and results["documents"][0]:
        for doc, metadata in zip(results["documents"][0], results["metadatas"][0]):
            retrieved_docs.append({
                "file": metadata.get("file_path", "unknown"),
                "scope": metadata.get("scope", "unknown"),
                "symbol_name": metadata.get("symbol_name", "unknown"),
                "content": doc
            })
            print(f"   ↳ Extracted relevant {metadata.get('scope')}: '{metadata.get('symbol_name')}' from {metadata.get('file_path')}")
            
    if not retrieved_docs:
        print("   ↳ ⚠️ Warning: No relevant code vectors found for this query.")

    return {
        "retrieved_code_vectors": retrieved_docs,
        "steps_taken": state.get("steps_taken", []) + ["live_routed"]
    }


def doc_agent_node(state: AgentState) -> Dict[str, Any]:
    print("📝 Agent Node [Doc Writer]: Generating production response via Gemini...")
    
    code_context = ""
    for vec in state["retrieved_code_vectors"]:
        code_context += f"\n--- FILE: {vec['file']} ({vec['scope']}: {vec['symbol_name']}) ---\n{vec['content']}\n"
    
    chat_history_context = ""
    for msg in state.get("messages", []):
        chat_history_context += f"👤 {msg['role'].capitalize()}: {msg['content']}\n"
    
    system_instruction = (
        "You are an expert technical AI assistant linked directly to a local codebase. "
        "Your job is to provide clean, technical, and accurate code summaries or answers using the "
        "retrieved code context assets and conversation history. Always format code references within "
        "proper markdown ticks."
    )
    
    user_prompt = ""
    if chat_history_context:
        user_prompt += f"Prior Conversation History:\n{chat_history_context}\n"
        
    user_prompt += f"Code Context Assets for Current Turn:\n{code_context}\n\n"
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
        except Exception as e:
            print(f"  ↳ ⚠️ Structured evaluation failed, falling back: {e}")
            eval_data = {
                "score": 5, "critique": "Fallback calculation applied.",
                "architecture_percentage": 50, "backend_logic_percentage": 50,
                "security_percentage": 50, "databases_percentage": 50, "scalability_percentage": 50,
                "flagged_weaknesses": []
            }

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

    persona_prompts = {
        "collaborator": "You are 'The Helpful Collaborator', a friendly pair-programmer. Guide the candidate gently, give conceptual hints, and treat this like a team project.",
        "traditionalist": "You are 'The Strict Traditionalist', an algorithm purist. Speak concisely, stay cold, and focus heavily on raw syntax rules, decoupling mechanics, and optimal design patterns.",
        "architect": "You are 'The Pragmatic Architect', a production startup tech lead. Focus strictly on real-world constraints, scalability bottlenecks, deployment friction, and operational safety."
    }

    base_persona = persona_prompts.get(state["interviewer_persona"], "You are an expert technical interviewer.")
    
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
# LangGraph Routing & Compilation Architecture
# =====================================================================

def mode_router(state: AgentState) -> str:
    """
    Splits application entry execution track paths based on session parameters.
    """
    if state.get("session_mode") == "interview":
        return "generate_interview_turn"
    return "write_docs"

def execution_router(state: AgentState) -> str:
    """
    Evaluates state flags to choose the next node path.
    """
    if state.get("session_mode") == "interview":
        return "end"
        
    if state.get("current_draft") and not state.get("review_feedback"):
        return "end"
    if state.get("review_feedback"):
        return "write_docs"
    return "write_docs"

# 1. Initialize the State Graph Blueprint
workflow = StateGraph(AgentState)

# 2. Register Processing Nodes (Including Interviewer Component)
workflow.add_node("route_and_fetch", router_node)
workflow.add_node("write_docs", doc_agent_node)
workflow.add_node("evaluate_quality", reviewer_node)
workflow.add_node("generate_interview_turn", interviewer_agent_node)

# 3. Configure Structural Edge Flows
workflow.set_entry_point("route_and_fetch")

# Dynamic execution branch selector edge
workflow.add_conditional_edges(
    "route_and_fetch",
    mode_router,
    {
        "write_docs": "write_docs",
        "generate_interview_turn": "generate_interview_turn"
    }
)

workflow.add_edge("write_docs", "evaluate_quality")
workflow.add_edge("generate_interview_turn", "evaluate_quality")

# Inject Conditional Routing Decisions for Completion Tracking
workflow.add_conditional_edges(
    "evaluate_quality",
    execution_router,
    {
        "write_docs": "write_docs",
        "end": END
    }
)

orchestrator_app = workflow.compile()