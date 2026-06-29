import os
from typing import TypedDict, List, Dict, Any
from dotenv import load_dotenv
from google import genai
from langgraph.graph import StateGraph, END
import chromadb

# Explicitly execute the environment variable loader
load_dotenv()

# Define the shared communication state between our agents
class AgentState(TypedDict):
    query: str
    retrieved_code_vectors: List[Dict[str, Any]]
    current_draft: str
    review_feedback: str
    steps_taken: List[str]

# Initialize the Gemini Generation Client
# It implicitly fetches GEMINI_API_KEY from your local .env file
ai_client = genai.Client()

def router_node(state: AgentState) -> Dict[str, Any]:
    print("🤖 Agent Node [Router]: Analyzing context and querying vector store...")
    
    # 1. Connect to our persistent disk storage folder
    chroma_client = chromadb.PersistentClient(path="./chroma_db_data")
    
    # 2. Bind to your exact Phase 1 collection name
    collection = chroma_client.get_collection(name="repository_methods")
    
    # 3. Query the collection using the active state text intent
    results = collection.query(
        query_texts=[state["query"]],
        n_results=2
    )
    
    # 4. Restructure the results using your actual metadata schema layout
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
    print("📝 Agent Node [Doc Writer]: Generating production markdown blocks via Gemini...")
    
    # 1. Format the extracted code snippets into an explicit context window block
    code_context = ""
    for vec in state["retrieved_code_vectors"]:
        code_context += f"\n--- FILE: {vec['file']} ({vec['scope']}: {vec['symbol_name']}) ---\n{vec['content']}\n"
    
    # 2. Build out the instruction prompt layout, appending any quality control feedback
    system_instruction = (
        "You are an expert technical documentation writer. Your job is to generate comprehensive, "
        "clean markdown documentation for the provided codebase blocks. Explain structural dependencies, "
        "inputs, and responsibilities clearly. Always format code references within proper markdown ticks."
    )
    
    user_prompt = f"User Request: {state['query']}\n\nCode Context Assets:\n{code_context}"
    if state.get("review_feedback"):
        user_prompt += f"\n\nCRITICAL - Previous Review Feedback to Correct:\n{state['review_feedback']}"

    # 3. Fire the live model execution thread
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config={"system_instruction": system_instruction}
    )
    
    # Check step sequence to trace modifications
    step_tag = "documented_fixed" if state.get("review_feedback") else "documented_initial"
    
    return {
        "current_draft": response.text,
        "review_feedback": "",  # Clear previous feedback tracking
        "steps_taken": state.get("steps_taken", []) + [step_tag]
    }


def reviewer_node(state: AgentState) -> Dict[str, Any]:
    print("🔬 Agent Node [Reviewer]: Evaluating documentation via Gemini QC...")
    
    # 1. Formulate strict verification criteria instructions
    system_instruction = (
        "You are a strict technical documentation QA reviewer. Analyze the provided draft documentation against "
        "the user's query. Ensure code blocks are correctly highlighted, technical statements are accurate, "
        "and formatting is immaculate.\n\n"
        "CRITICAL OUTPUT FORMAT:\n"
        "- If the documentation passes review completely, output EXACTLY the phrase: APPROVED\n"
        "- If it fails, explicitly state what specific formatting or structural adjustments are required."
    )
    
    user_prompt = f"User Original Query: {state['query']}\n\nCurrent Documentation Draft:\n{state['current_draft']}"
    
    # 2. Fire the live model review checkpoint thread
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config={"system_instruction": system_instruction}
    )
    
    review_text = response.text.strip()
    steps = state.get("steps_taken", [])
    
    # 3. Route state flags based on the model's textual determination
    if "APPROVED" in review_text:
        print("   ↳ Quality check: PASSED ✅")
        return {
            "review_feedback": "",
            "steps_taken": steps + ["reviewed_pass"]
        }
    else:
        print(f"   ↳ Quality check: FAILED ❌ (Feedback provided)")
        return {
            "review_feedback": review_text,
            "steps_taken": steps + ["reviewed_fail"]
        }

# =====================================================================
# LangGraph Routing & Compilation Architecture
# =====================================================================

def execution_router(state: AgentState) -> str:
    """
    Evaluates state flags to choose the next node path.
    """
    # If a draft has been reviewed and has no feedback, finalize the run
    if state.get("current_draft") and not state.get("review_feedback"):
        return "end"
    # If the reviewer found structural flaws, bounce back to the doc writer
    if state.get("review_feedback"):
        return "write_docs"
    # Default fallback to generation phase
    return "write_docs"

# 1. Initialize the State Graph Blueprint
workflow = StateGraph(AgentState)

# 2. Register our Processing Nodes
workflow.add_node("route_and_fetch", router_node)
workflow.add_node("write_docs", doc_agent_node)
workflow.add_node("evaluate_quality", reviewer_node)

# 3. Configure the Structural Edge Flow
workflow.set_entry_point("route_and_fetch")
workflow.add_edge("route_and_fetch", "write_docs")
workflow.add_edge("write_docs", "evaluate_quality")

# 4. Inject the Conditional Routing Decisions
workflow.add_conditional_edges(
    "evaluate_quality",
    execution_router,
    {
        "write_docs": "write_docs",
        "end": END
    }
)

# 5. Compile the Workflow Engine into an Executable Application
orchestrator_app = workflow.compile()

# Test execution block to verify the state lifecycle pipelines cleanly
if __name__ == "__main__":
    test_state = {
        "query": "Document the internal structure of parser.py",
        "retrieved_code_vectors": [],
        "current_draft": "",
        "review_feedback": "",
        "steps_taken": []
    }
    
    print("🚀 Initializing test run across LangGraph workflow pipeline...")
    final_output = orchestrator_app.invoke(test_state)
    print("\n🏁 Execution complete! Sequence of steps taken:", final_output["steps_taken"])
    
    # -----------------------------------------------------------------
    # Production File Exporter Setup
    # -----------------------------------------------------------------
    if final_output.get("current_draft"):
        # Create a docs directory if it doesn't already exist
        output_dir = "./docs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Define a clean target file name
        file_name = "parser_documentation.md"
        file_path = os.path.join(output_dir, file_name)
        
        # Write the active draft content to disk
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(final_output["current_draft"])
            
        print(f"\n💾 Success! Clean documentation successfully written to disk at: {file_path}")