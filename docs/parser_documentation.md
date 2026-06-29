This document provides a detailed breakdown of the `parser.py` module, focusing on its internal structure, functionality, and how it processes Python source code.

## Module: `analyzer/parser.py`

The `parser.py` module is responsible for analyzing individual Python files and extracting their structural metadata using Python's Abstract Syntax Tree (AST).

### Function: `parse_python_file`

Analyzes a given Python file, extracts its classes, methods, and standalone functions, and organizes this information into a structured dictionary.

-   **Path:** `./analyzer/parser.py`
-   **Dependencies:** `ast` (Python's built-in module for AST parsing).
-   **Used by:** `analyzer/crawler.py` (specifically by the `crawl_repository` function).

#### Purpose

This function reads a Python source file, parses it into an Abstract Syntax Tree (AST), and then traverses the tree to identify and extract metadata about classes, their methods, and standalone functions defined at the top level of the file.

#### Parameters

-   `file_path` (`str`): The absolute or relative path to the Python file to be parsed.

#### Returns

-   `dict`: A dictionary containing the parsed metadata of the file, structured as follows:
    ```python
    {
        'file_path': str,  # The path of the file that was parsed
        'classes': [
            {
                'name': str,        # Name of the class
                'docstring': str,   # Docstring of the class (or None)
                'methods': [
                    {
                        'name': str,            # Name of the method
                        'args': list[str],      # List of argument names
                        'docstring': str,       # Docstring of the method (or None)
                        'source_code': str      # Unparsed source code of the method
                    },
                    # ... more methods
                ]
            },
            # ... more classes
        ],
        'standalone_functions': [
            {
                'name': str,            # Name of the function
                'args': list[str],      # List of argument names
                'docstring': str,       # Docstring of the function (or None)
                'source_code': str      # Unparsed source code of the function
            },
            # ... more standalone functions
        ]
    }
    ```
-   `None`: If a `SyntaxError` occurs during parsing, a message is printed, and `None` is returned.

#### Internal Logic

1.  **File Reading:**
    -   Opens the file specified by `file_path` in read mode (`'r'`) with UTF-8 encoding.
    -   Reads the entire content of the file into the `source_code` variable.

2.  **AST Parsing:**
    -   Attempts to parse the `source_code` into an AST using `ast.parse(source_code)`.
    -   **Error Handling:** If `ast.parse` raises a `SyntaxError` (e.g., due to malformed Python code), it prints an error message to the console and returns `None`, skipping the problematic file.

3.  **Metadata Initialization:**
    -   Initializes an empty dictionary `file_metadata` with `file_path` and empty lists for `classes` and `standalone_functions`. This dictionary will accumulate the extracted data.

4.  **AST Traversal:**
    -   Iterates through each top-level node (`node`) in the `tree.body` (representing the main statements/definitions in the file).
    -   **Class Definition Handling (`ast.ClassDef`):**
        -   If a `node` is an instance of `ast.ClassDef`, it indicates a class definition.
        -   Extracts the class `name` (`node.name`) and its `docstring` using `ast.get_docstring(node)`.
        -   Initializes an empty `methods` list within the `class_info` dictionary.
        -   It then iterates through the `sub_node`s within the class body (`node.body`).
        -   **Method Definition Handling (`ast.FunctionDef` within a class):**
            -   If a `sub_node` is an `ast.FunctionDef`, it's treated as a method.
            -   Extracts the method `name` (`sub_node.name`), its arguments (`args` from `sub_node.args.args`), `docstring` (`ast.get_docstring(sub_node)`), and the raw `source_code` of the method itself using `ast.unparse(sub_node)`.
            -   Appends the `method_info` to the `methods` list of the current `class_info`.
        -   Finally, appends the complete `class_info` to `file_metadata['classes']`.
    -   **Standalone Function Definition Handling (`ast.FunctionDef`):**
        -   If a `node` is an instance of `ast.FunctionDef` (and not part of a class, handled by the `elif`), it represents a top-level standalone function.
        -   Extracts the function `name` (`node.name`), arguments (`args`), `docstring`, and `source_code` in a similar manner to methods.
        -   Appends the `func_info` to `file_metadata['standalone_functions']`.

5.  **Result Return:**
    -   Returns the populated `file_metadata` dictionary.

#### Example Usage (Conceptual)

```python
# Assuming 'my_module.py' contains a class and a standalone function
# from analyzer.parser import parse_python_file

# parsed_data = parse_python_file('path/to/my_module.py')
# if parsed_data:
#     print(parsed_data['file_path'])
#     for cls in parsed_data['classes']:
#         print(f"  Class: {cls['name']}")
#         for method in cls['methods']:
#             print(f"    Method: {method['name']} (Args: {method['args']})")
#     for func in parsed_data['standalone_functions']:
#         print(f"  Function: {func['name']} (Args: {func['args']})")
```