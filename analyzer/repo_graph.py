import os
import ast
import json
import re
from typing import Dict, Any, List

class CodebaseGraphAnalyzer(ast.NodeVisitor):
    """AST visitor to map out functions, imports, and classes inside a single Python file."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.meta = {
            "language": "python",
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
        if self.current_class:
            self.meta["classes"][self.current_class]["methods"].append(func_name)
        else:
            self.meta["standalone_functions"].append(func_name)
        self.generic_visit(node)


def parse_js_ts_file(file_path: str, content: str) -> Dict[str, Any]:
    """Extracts symbols, exports, and imports from JavaScript/TypeScript files using optimized regex scanning."""
    meta = {
        "language": "javascript/typescript",
        "imports": [],
        "classes": {},
        "standalone_functions": []
    }
    
    # 1. Match ES6 and CommonJS imports
    # Match: import { X } from 'Y' or import X from "Y"
    es6_imports = re.findall(r"(?:import|from)\s+['\"]([^'\"]+)['\"]", content)
    # Match: require('Y')
    commonjs_imports = re.findall(r"require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)", content)
    
    for imp in set(es6_imports + commonjs_imports):
        if not imp.startswith("."):  # Focus primarily on package/boundary modules
            meta["imports"].append(imp)

    # 2. Match Classes
    classes = re.findall(r"class\s+(\w+)(?:\s+extends\s+(\w+))?", content)
    for cls, base in classes:
        meta["classes"][cls] = {
            "methods": [],
            "base_classes": [base] if base else []
        }

    # 3. Match Functions and Methods
    # Standalone or exported functions: function name(), const name = () => {}
    found_functions = re.findall(r"function\s+(\w+)\s*\(", content)
    found_arrow_funcs = re.findall(r"(?:const|let|var)\s+(\w+)\s*=\s*(?:\([^)]*\)|_\w*)\s*=>", content)
    
    for func in set(found_functions + found_arrow_funcs):
        meta["standalone_functions"].append(func)
        
    return meta


def generate_repository_graph(root_dir: str) -> Dict[str, Any]:
    """Crawl the workspace to compile a high-level Python & JS/TS dependency and structural graph map."""
    repo_graph = {
        "project_root": os.path.basename(os.path.abspath(root_dir)),
        "manifest_dependencies": {},
        "directory_tree": {},
        "modules": {}
    }

    # Extract package.json if it exists at the root level
    package_json_path = os.path.join(root_dir, "package.json")
    if os.path.exists(package_json_path):
        try:
            with open(package_json_path, "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
                repo_graph["manifest_dependencies"] = {
                    **pkg_data.get("dependencies", {}),
                    **pkg_data.get("devDependencies", {})
                }
        except Exception as e:
            repo_graph["manifest_dependencies"] = {"error": f"Failed to parse package.json: {e}"}

    supported_extensions = (".py", ".js", ".ts", ".jsx", ".tsx")

    for root, dirs, files in os.walk(root_dir):
        # Filter noise paths
        if any(ignored in root for ignored in [".git", "__pycache__", "node_modules", "venv", ".venv", "chroma_db", "storage", "scorecards", "dist", "build", ".next"]):
            continue
            
        rel_path = os.path.relpath(root, root_dir)
        dir_key = "root" if rel_path == "." else rel_path
        
        # Log structured file hierarchy map
        tracked_files = [f for f in files if f.endswith(supported_extensions)]
        if tracked_files:
            repo_graph["directory_tree"][dir_key] = tracked_files

        for file in files:
            if file.endswith(supported_extensions):
                full_path = os.path.join(root, file)
                module_key = os.path.relpath(full_path, root_dir).replace(os.sep, "/")
                
                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        file_content = f.read()
                        
                    if file.endswith(".py"):
                        tree = ast.parse(file_content, filename=file)
                        analyzer = CodebaseGraphAnalyzer(module_key)
                        analyzer.visit(tree)
                        repo_graph["modules"][module_key] = analyzer.meta
                    else:
                        # Process via our JavaScript/TypeScript structural parser
                        repo_graph["modules"][module_key] = parse_js_ts_file(module_key, file_content)
                        
                except Exception as e:
                    repo_graph["modules"][module_key] = {"error": f"Failed to parse source tree elements: {e}"}

    # Save compile blueprint map to disk
    output_path = os.path.join(root_dir, "repo_blueprint.json")
    with open(output_path, "w", encoding="utf-8") as out:
        json.dump(repo_graph, out, indent=4)
        
    print(f"🎯 [Repository Graph]: Blueprint map successfully compiled to '{output_path}'.")
    return repo_graph

if __name__ == "__main__":
    generate_repository_graph(".")