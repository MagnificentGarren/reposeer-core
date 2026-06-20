import ast
import json

def parse_python_file(file_path: str):
    """
    This function will read a Python file and turn its structure into data.
    """
    # 1. Open and read the raw text of the target file
    with open(file_path, "r", encoding="utf-8") as source_file:
        source_code = source_file.read()

    # 2. Convert the raw text into an Abstract Syntax Tree (AST)
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        print(f"Skipping {file_path} due to a syntax error: {e}")
        return None

    # 3. Create a layout dictionary to hold our extracted data
    file_metadata = {
        "file_path": file_path,
        "classes": [],
        "standalone_functions": []
    }

    # 4. Loop through the blocks in the file to find Classes and Functions
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "docstring": ast.get_docstring(node),
                "methods": []
            }
            
            # Check everything inside the class body for methods
            for sub_node in node.body:
                if isinstance(sub_node, ast.FunctionDef):
                    method_info = {
                        "name": sub_node.name,
                        "args": [arg.arg for arg in sub_node.args.args],
                        "docstring": ast.get_docstring(sub_node),
                        "source_code": ast.unparse(sub_node)
                    }
                    class_info["methods"].append(method_info)
            
            file_metadata["classes"].append(class_info)

        # 5. Check for standalone functions
        elif isinstance(node, ast.FunctionDef):
            func_info = {
                "name": node.name,
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node),
                "source_code": ast.unparse(node)
            }
            file_metadata["standalone_functions"].append(func_info)
    
    return file_metadata


# =====================================================================
# TEST HARNESS: This runs ONLY when you execute this file directly.
# =====================================================================
if __name__ == "__main__":
    import os

    # Let's write a quick temporary file to test our new engine on
    sample_code = """
class PaymentService:
    \"\"\"Handles application processing fees.\"\"\"
    
    def process_invoice(self, invoice_id: int, amount: float):
        \"\"\"Validates and pays an invoice total.\"\"\"
        print(f"Paying {amount}")
        return True

def calculate_vat(price: float) -> float:
    \"\"\"Standard VAT calculator helper.\"\"\"
    return price * 0.15
"""
    
    # Write the sample file to disk
    with open("sample_target.py", "w") as test_file:
        test_file.write(sample_code)
        
    # Run our extraction logic on the sample file
    parsed_data = parse_python_file("sample_target.py")
    
    # Print out the structured data nicely formatted
    print(json.dumps(parsed_data, indent=4))
    
    # Clean up and remove the temporary sample file
    if os.path.exists("sample_target.py"):
        os.remove("sample_target.py")