from pathlib import Path
import os
import re
import itertools

DOCS_DIR = (Path(__file__).parent.parent / "docs").resolve()

def list_all_docs(pattern = "*.md"):
    """List all documents in the docs directory.
    Args:
        pattern (str, optional): The glob pattern to match files. Defaults to "*.md".
    Returns:
        list: A list of all matching files relative to the docs directory.
    """
    files = []
    for file in DOCS_DIR.rglob(pattern):
        files.append(file.relative_to(DOCS_DIR))
    return files

def grep(pattern, max_results = 5):
    """Search for a pattern in all markdown files in the docs directory.
    Args:        pattern (str): The word to search for.
        max_results (int, optional): The maximum number of results to return. Defaults to 5.
    Returns:        list: A list of strings in the format "relative_path:line_number:line_content
    """

    results = []
    rx = re.compile(pattern)
    for path in DOCS_DIR.rglob("*.md"):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f, start=1):
                if rx.search(line):
                    results.append(f"{path.relative_to(DOCS_DIR)}:{i}:{line.rstrip('\n')}")
                    if len(results) >= max_results:
                        return results
    return results


def read_slice_doc(path, start_line, end_line):
    """Read a slice of a document in the docs directory.
    Args:
        path (str): The path to the document relative to the docs directory.
        start_line (int): The starting line number (1-based).
        end_line (int): The ending line number (inclusive).
    Returns:
        str: The content of the specified slice of the document.
    """
    target  = (DOCS_DIR / path).resolve()

    if not target.is_relative_to(DOCS_DIR):
        return "Error: Invalid path. The file must be within the docs directory."

    with open(target, 'r', encoding='utf-8', errors='ignore') as f:
        if end_line is not None:
            chunk = itertools.islice(f, start_line - 1, end_line)
        else:
            chunk = itertools.islice(f, start_line - 1, None)
        return "".join(chunk)

def read_doc(path):
    """Read the content of a document in the docs directory.
    Args:
        path (str): The path to the document relative to the docs directory.
    Returns:
        str: The content of the document.
    """
    target = (DOCS_DIR / path).resolve()

    if not target.is_relative_to(DOCS_DIR):
        return "Error: Invalid path. The file must be within the docs directory."
    
    if not target.is_file():
        return "Error: File not found."
    
    return target.read_text()

