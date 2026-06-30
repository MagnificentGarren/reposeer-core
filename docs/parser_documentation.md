The `parser.py` module contains the `parse_python_file` function, which is designed to analyze a given Python file and extract its structural metadata.

The internal structure of `parser.py` revolves around this single function:

*   **`parse_python_file(file_path: str)`**
    *   **Purpose:** Reads a Python file, parses its Abstract Syntax Tree (AST), and extracts information about classes, methods, and standalone functions.
    *   **Input:** Takes a `file_path` (string) pointing to a Python file.
    *   **Process:**
        1.  Opens and reads the content of the specified Python file.
        2.  Uses Python's built-in `ast.parse()` to construct an AST from the source code.
        3.  Includes error handling with a `try-except` block to catch `SyntaxError` during AST parsing, printing an error message and returning `None` if an error occurs.
        4.  Initializes a `file_metadata` dictionary with the `file_path` and empty lists for `classes` and `standalone_functions`.
        5.  Iterates through the top-level nodes of the AST (`tree.body`):
            *   If a node is an `ast.ClassDef` (class definition):
                *   It extracts the class `name` and `docstring`.
                *   It then iterates through the class's body to find `ast.FunctionDef` nodes (method definitions).
                *   For each method, it extracts its `name`, `args` (argument names), `docstring`, and the full `source_code` of the method (using `ast.unparse()`).
                *   This method information is stored in a list within the class's metadata.
                *   The complete class information is then appended to the `file_metadata['classes']` list.
            *   If a node is an `ast.FunctionDef` (standalone function definition):
                *   It extracts the function `name`, `args`, `docstring`, and `source_code`.
                *   This function information is appended to the `file_metadata['standalone_functions']` list.
    *   **Output:** Returns a dictionary named `file_metadata` with the following structure:
        ```python
        {
            'file_path': 'path/to/your/file.py',
            'classes': [
                {
                    'name': 'ClassName',
                    'docstring': 'Docstring for ClassName.',
                    'methods': [
                        {
                            'name': 'method_name',
                            'args': ['self', 'arg1', 'arg2'],
                            'docstring': 'Docstring for method_name.',
                            'source_code': 'def method_name(self, arg1, arg2):\n    pass'
                        },
                        # ... other methods ...
                    ]
                },
                # ... other classes ...
            ],
            'standalone_functions': [
                {
                    'name': 'function_name',
                    'args': ['argA', 'argB'],
                    'docstring': 'Docstring for function_name.',
                    'source_code': 'def function_name(argA, argB):\n    pass'
                },
                # ... other standalone functions ...
            ]
        }
        ```
        If a syntax error occurs, it returns `None`.

This function serves as the core parsing logic that the `crawler.py` module utilizes to process multiple Python files.