import os
import chromadb

def get_vector_collection():
    """
    Initializes a persistent database storage folder on disk 
    and sets up an indexing collection.
    """
    # Create a local storage folder inside your project directory
    storage_dir = os.path.join(os.getcwd(), "chroma_db_data")
    
    # Initialize the persistent client pointing to that folder
    client = chromadb.PersistentClient(path=storage_dir)
    
    # Get or create an isolated collection for our project code snippets
    collection = client.get_or_create_collection(name="repository_methods")
    return collection

def store_codebase_vectors(parsed_files_list: list):
    """
    Takes the code mapping array from our crawler, isolates the code blocks,
    and inserts them directly into our vector storage engine.
    """
    collection = get_vector_collection()
    
    # Tracking variables for batch injection
    documents = []
    metadatas = []
    ids = []
    counter = 1

    for file_info in parsed_files_list:
        file_path = file_info["file_path"]

        # Loop through methods inside discovered classes
        for cls in file_info["classes"]:
            class_name = cls["name"]
            for method in cls["methods"]:
                # The text block the vector model will evaluate
                documents.append(method["source_code"])
                
                # Metadata lets the AI filter or link back to specific targets later
                metadatas.append({
                    "file_path": file_path,
                    "scope": "class_method",
                    "parent_symbol": class_name,
                    "symbol_name": method["name"],
                    "docstring": method["docstring"] or ""
                })
                
                ids.append(f"id_symbol_{counter}")
                counter += 1

        # Loop through standalone context functions
        for func in file_info["standalone_functions"]:
            documents.append(func["source_code"])
            metadatas.append({
                "file_path": file_path,
                "scope": "standalone_function",
                "parent_symbol": "None",
                "symbol_name": func["name"],
                "docstring": func["docstring"] or ""
            })
            ids.append(f"id_symbol_{counter}")
            counter += 1

    # Safe checking: Only upsert if documents exist
    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"\n Successfully embedded and stored {len(documents)} functional code vectors.")
    else:
        print("\nNo functional code blocks found to embed.")

# =====================================================================
# TEST HARNESS: Verifies vector parsing using our own codebase files
# =====================================================================
if __name__ == "__main__":
    from analyzer.crawler import crawl_repository
    
    print("Step 1: Parsing the 'analyzer' folder codebase...")
    repo_data = crawl_repository("./analyzer")
    
    print("\nStep 2: Transforming code into vector coordinates...")
    store_codebase_vectors(repo_data)