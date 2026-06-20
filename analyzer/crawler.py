import os
from analyzer.parser import parse_python_file

def crawl_repository(repo_path: str) -> list:
    """
    Sifts through a directory recursively, finds all Python files,
    and runs them through our AST parser.
    """
    all_parsed_data = []

    # Check if the folder path actually exists before walking it
    if not os.path.exists(repo_path):
        print(f"Error: The path '{repo_path}' does not exist.")
        return all_parsed_data

    # os.walk loops through folders, subfolders, and files
    for root, dirs, files in os.walk(repo_path):
        
        # Performance/Safety Skip: Skip hidden directories (like .git) or virtual environments
        # Modifying dirs in-place tells os.walk not to look down these branches
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__', 'env']]

        for file in files:
            # We are targeting only Python files for this initial sprint
            if file.endswith(".py"):
                full_file_path = os.path.join(root, file)
                
                print(f"Scanning: {full_file_path}")
                
                # Use the parser we built in Step 1.1
                file_data = parse_python_file(full_file_path)
                
                if file_data:
                    all_parsed_data.append(file_data)

    return all_parsed_data


# =====================================================================
# TEST HARNESS: Verifies the crawler can scan the 'analyzer' folder itself
# =====================================================================
if __name__ == "__main__":
    import json

    print("Starting a test scan on our own 'analyzer' directory...\n")
    
    # Let's test the crawler by telling it to scan our current analyzer folder
    results = crawl_repository("./analyzer")
    
    print(f"\nScan complete. Successfully parsed {len(results)} files.")
    # Show a snippet of what it found
    print(json.dumps(results, indent=2))