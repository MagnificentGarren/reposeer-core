import os
from datetime import datetime
from typing import Dict, List, Any

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scorecards")

def export_session_report(metadata: Dict[str, Any], scores: Dict[str, float], weaknesses: List[str], grades: List[Dict[str, Any]]) -> str:
    """
    Compiles session evaluation metrics into a beautifully structured Markdown report file.
    """
    # Ensure the output scorecards directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    now = datetime.now()
    timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")
    file_safe_date = now.strftime("%Y%m%d_%H%M%S")
    
    filename = f"scorecard_{metadata['interviewer_persona']}_{file_safe_date}.md"
    full_path = os.path.join(OUTPUT_DIR, filename)
    
    # Map percentages to status indicators for the Knowledge Map section
    def get_status_emoji(percentage: float) -> str:
        if percentage >= 85: return "✅ Proficient"
        if percentage >= 60: return "⚠️ Developing"
        return "❌ Critical Focus"

    # Compile the Markdown payload string
    md_content = f"""# 📊 Technical Evaluation Performance Report
**Generated:** `{timestamp_str}`  
**Track Mode:** `{metadata['session_mode'].upper()}`  
**Target Difficulty:** `{metadata['difficulty'].upper()}`  
**Assigned Interviewer Archetype:** `{metadata['interviewer_persona'].upper()}`

---

## 📈 Core Engineering Pillars Breakdown

| Technical Competency Pillar | Score Percentage | Status Assessment |
| :--- | :---: | :--- |
| 🏗️ Architecture & Structural Design | {scores['Architecture']:.1f}% | {get_status_emoji(scores['Architecture'])} |
| ⚙️ Backend Logic & Syntax Execution | {scores['Backend Logic']:.1f}% | {get_status_emoji(scores['Backend Logic'])} |
| 🔒 Security, Vulnerabilities & Bounds | {scores['Security']:.1f}% | {get_status_emoji(scores['Security'])} |
| 🗄️ Databases, Indexing & Data Flow | {scores['Databases']:.1f}% | {get_status_emoji(scores['Databases'])} |
| 🚀 Scalability, Benchmarks & Big-O | {scores['Scalability']:.1f}% | {get_status_emoji(scores['Scalability'])} |

---

## 🔍 Conceptual Weakness Tracker
The evaluator flagged the following specific domain gaps during this session. These tags have been synced to your persistent memory ledger to optimize future interview focus variants:

"""
    if weaknesses:
        for topic in set(weaknesses):
            md_content += f"- ⚠️ `{topic.strip().lower()}`\n"
    else:
        md_content += "- 🎉 No systemic critical weaknesses flagged this round. Exceptional performance.\n"
        
    md_content += "\n---\n\n## 📌 Question-by-Question Evaluation History\n"
    
    for grade in grades:
        md_content += f"### ❓ Question #{grade['question_num']}\n"
        # Format raw terminal output text blocks into clean markdown quotes
        formatted_eval = grade['raw_evaluation'].replace("\n", "\n> ")
        md_content += f"> {formatted_eval}\n\n"
        md_content += "--- \n\n"
        
    md_content += "🤖 *Keep refining your codebase architecture and pushing boundaries. Session End.*"
    
    # Write report file to disk
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(md_content.strip())
        
    print(f"📋 [Report Exporter]: Performance scorecard successfully saved to '{full_path}'.")
    return full_path