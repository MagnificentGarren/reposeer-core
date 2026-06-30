import sys
import random
from agents.orchestrator import orchestrator_app
import os
import json

def display_welcome_banner():
    print("\n" + "=" * 75)
    print("🎙️  REPOSEER-CORE: THE INTELLIGENT TECHNICAL INTERVIEW SIMULATOR")
    print("    Prepare for code reviews, technical rounds, and engineering panels.")
    print("=" * 75)

def setup_session():
    """
    Prompts the user to select their track, difficulty level, 
    and randomly configures an interviewer personality if needed.
    """
    display_welcome_banner()
    
    # 1. Track Selection
    print("\nSelect Your Training Track:")
    print("  [1] Casual Mode (Study & Explore codebase freely)")
    print("  [2] Interviewer Mode (5-Question Mock Exam simulation)")
    
    while True:
        choice = input("\n👉 Choose track (1 or 2): ").strip()
        if choice in ["1", "2"]:
            mode = "casual" if choice == "1" else "interview"
            break
        print("❌ Invalid selection. Please enter 1 or 2.")
        
    # 2. Difficulty Level Selection
    print("\nSelect Technical Target Difficulty:")
    print("  [Easy]   - Core Syntax, logic flow, and basic modular components")
    print("  [Medium] - Edge-case validation, state pipelines, and system logic")
    print("  [Hard]   - Concurrency limits, scale bottlenecks, and deep optimizations")
    
    while True:
        diff_input = input("\n👉 Enter difficulty (easy, medium, hard): ").strip().lower()
        if diff_input in ["easy", "medium", "hard"]:
            difficulty = diff_input
            break
        print("❌ Invalid choice. Please type 'easy', 'medium', or 'hard'.")
        
    # 3. Persona Assignment
    persona = "none"
    if mode == "interview":
        personas = ["collaborator", "traditionalist", "architect"]
        persona = random.choice(personas)
        
        persona_titles = {
            "collaborator": "🤝 The Helpful Collaborator (Senior Pair-Programmer)",
            "traditionalist": "⏱️  The Strict Traditionalist (Algorithm Purist)",
            "architect": "🎯 The Pragmatic Architect (Startup Tech Lead)"
        }
        
        print("\n" + "-" * 75)
        print(f"🔒 ASSIGNED INTERVIEWER: {persona_titles[persona]}")
        print("   They have reviewed your database indexes and are preparing questions...")
        print("-" * 75)
    else:
        print("\n" + "-" * 75)
        print("🧠 CASUAL MENTOR ACTIVATED: Ask anything about your codebase files.")
        print("-" * 75)
        
    return mode, difficulty, persona

def launch_chat_engine():
    mode, difficulty, persona = setup_session()
    conversation_history = []
    
    # Maintain the running scorecard evaluation array across turns
    running_scores = []
    
    # Internal index counter for tracking interview turns
    q_index = 1 if mode == "interview" else 0

    while True:
        try:
            # If we are in interview mode and just starting out, let the interviewer ask the first question
            if mode == "interview" and q_index == 1 and len(conversation_history) == 0:
                print("\n⚙️  Initializing mock board. Generating question 1 of 5...")
                user_query = "INITIALIZE_INTERVIEW_SESSION"
            else:
                user_query = input("\n💬 You: ").strip()
                if not user_query:
                    continue
                if user_query.lower() in ["exit", "quit"]:
                    print("\n🔌 Closing the simulator. Keep pushing commits. Goodbye!")
                    break

            print("\n⚙️  Processing response through agent nodes...")
            
            # 🎯 DYNAMIC BLUEPRINT INJECTION: Always load fresh structure on every loop pass
            blueprint_data = {}
            if os.path.exists("repo_blueprint.json"):
                try:
                    with open("repo_blueprint.json", "r", encoding="utf-8") as f:
                        blueprint_data = json.load(f)
                except Exception as e:
                    print(f"  ↳ ⚠️  [State Sync Warning]: Could not parse repo_blueprint.json: {e}")

            # Map out state payload config per turn, pulling from running scores array cache
            input_state = {
                "query": user_query,
                "messages": conversation_history,
                "retrieved_code_vectors": [],
                "repo_blueprint": blueprint_data,  # ◄── Graph Map injected right here
                "current_draft": "",
                "review_feedback": "",
                "steps_taken": [],
                "session_mode": mode,
                "difficulty": difficulty,
                "interviewer_persona": persona,
                "current_question_index": q_index,
                "evaluation_scores": running_scores
            }
            
            # Only append to chat history if it wasn't the auto-init engine flag
            if user_query != "INITIALIZE_INTERVIEW_SESSION":
                conversation_history.append({"role": "user", "content": user_query})

            final_state = orchestrator_app.invoke(input_state)
            agent_response = final_state.get("current_draft", "⚠️ Error: Generation failed.")
            
            conversation_history.append({"role": "assistant", "content": agent_response})
            
            # Save the latest generated scorecard updates safely back to our persistent local cache
            if "evaluation_scores" in final_state:
                running_scores = final_state["evaluation_scores"]
            
            print(f"\n🤖 Response:")
            print("-" * 60)
            print(agent_response)
            print("-" * 60)
            
            # Increment tracking index loop if we are in exam mode
            # Increment tracking index loop if we are in exam mode
            if mode == "interview":
                # Let the user complete all 5 questions before compiling the report
                if q_index >= 5:
                    print("\n🏁 Technical evaluation round complete! Compiling your final scorecard...")
                    print("\n" + "=" * 75)
                    print("📊 OFFICIAL REPOSEER-CORE TECHNICAL EVALUATION PERFORMANCE REPORT")
                    print("=" * 75)
                    
                    # Track structural aggregates for storage
                    avg_metrics = {"Architecture": 0.0, "Backend Logic": 0.0, "Security": 0.0, "Databases": 0.0, "Scalability": 0.0}
                    all_weaknesses = []
                    
                    if running_scores:
                        for grade in running_scores:
                            print(f"\n📌 QUESTION #{grade['question_num']} EVALUATION:")
                            print(grade['raw_evaluation'])
                            print("-" * 50)
                            
                            # Aggregate structured JSON items if available
                            payload = grade.get("json_payload")
                            if payload:
                                avg_metrics["Architecture"] += payload["architecture_percentage"] / 5
                                avg_metrics["Backend Logic"] += payload["backend_logic_percentage"] / 5
                                avg_metrics["Security"] += payload["security_percentage"] / 5
                                avg_metrics["Databases"] += payload["databases_percentage"] / 5
                                avg_metrics["Scalability"] += payload["scalability_percentage"] / 5
                                all_weaknesses.extend(payload.get("flagged_weaknesses", []))
                        
                       # -------------------------------------------------------------
                        # Sync To SQLite Memory Ledger Database
                        # -------------------------------------------------------------
                        meta_payload = {
                            "session_mode": mode,
                            "difficulty": difficulty,
                            "interviewer_persona": persona
                        }
                        # Deduplicate topic tags safely
                        unique_weaknesses = list(set(all_weaknesses))
                        
                        from storage.memory_ledger import log_completed_session
                        log_completed_session(meta_payload, avg_metrics, unique_weaknesses)
                        
                        # -------------------------------------------------------------
                        # Export Structured Markdown Scorecard Report (Destination A)
                        # -------------------------------------------------------------
                        from storage.report_exporter import export_session_report
                        export_session_report(meta_payload, avg_metrics, unique_weaknesses, running_scores)
                    else:
                        print("\n⚠️ Note: No answer entries were recorded for scoring evaluation.")
                        
                    print("\n" + "=" * 75)
                    print("🚀 Keep refining your codebase architecture and pushing boundaries. Session End.")
                    print("=" * 75)
                    break
                    
                q_index += 1
            
        except KeyboardInterrupt:
            print("\n\n🔌 Session terminated via keyboard. Exiting...")
            sys.exit(0)

if __name__ == "__main__":
    launch_chat_engine()