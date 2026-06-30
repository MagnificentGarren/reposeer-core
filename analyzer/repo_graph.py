import os
import ast
import json
from typing import Dict, Any, List

class CodebaseGraphAnalyzer(ast.NodeVisitor):
    """AST visitor to map out functions, imports, and classes inside a single file."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.meta = {
            "imports": [],
            "classes": {},
            "standalone_functions": []
        }
        self.current_class = None

    def visit_Import(self, node):
        for alias in node.names:
            self.meta["imports"].append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.meta["imports"].append(node.module)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_name = node.name
        self.meta["classes"][class_name] = {
            "methods": [],
            "base_classes": [ast.unparse(b) for b in node.bases]
        }
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node):
        func_name = node.name
        # Check if function is a method inside a class or standalone
        if self.current_class:
            self.meta["classes"][self.current_class]["methods"].append(func_name)
        else:
            self.meta["standalone_functions"].append(func_name)
        self.generic_visit(node)

def generate_repository_graph(root_dir: str) -> Dict[str, Any]:
    """Crawl the project workspace to compile a high-level dependency and structural graph map."""
    repo_graph = {
        "project_root": os.path.basename(os.path.abspath(root_dir)),
        "directory_tree": {},
        "modules": {}
    }

    for root, dirs, files in os.walk(root_dir):
        # Ignore common noise blocks
        if any(ignored in root for ignored in [".git", "__pycache__", "venv", ".venv", "chroma_db", "storage"]):
            continue
            
        rel_path = os.path.relpath(root, root_dir)
        dir_key = "root" if rel_path == "." else rel_path
        repo_graph["directory_tree"][dir_key] = [f for f in files if f.endswith(".py")]

        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                module_key = os.path.relpath(full_path, root_dir).replace(os.sep, ".")
                
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=file)
                    
                    analyzer = CodebaseGraphAnalyzer(module_key)
                    analyzer.visit(tree)
                    repo_graph["modules"][module_key] = analyzer.meta
                except Exception as e:
                    repo_graph["modules"][module_key] = {"error": f"Failed to parse AST: {e}"}

    # Save to disk as our master structural context provider
    output_path = os.path.join(root_dir, "repo_blueprint.json")
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(repo_graph, out, indent=4)
        
    print(f"🎯 [Repository Graph]: Blueprint map successfully compiled to '{output_path}'.")
    return repo_graph

if __name__ == "__main__":
    # Point to current directory setup
    generate_repository_graph(".")