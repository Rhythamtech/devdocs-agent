from pathlib import Path
import re
import itertools
from contextvars import ContextVar

# ContextVar for request-local uploads folder
current_user_docs_dir: ContextVar[Path] = ContextVar("current_user_docs_dir", default=None)

def get_docs_dir() -> Path:
    val = current_user_docs_dir.get()
    if val is not None:
        return val
    # Fallback to default docs directory
    return (Path(__file__).parent.parent / "docs").resolve()

def list_all_docs(pattern: str = "*"):
    """List all documents (markdown and text files) in the document directory.
    Args:
        pattern (str, optional): Ignored. Defaults to "*".
    Returns:
        list: A list of all matching files relative to the document directory.
    """
    docs_dir = get_docs_dir()
    if not docs_dir.exists():
        return []
    files = []
    # Find both .md and .txt files
    for ext in ("*.md", "*.txt"):
        for file in docs_dir.rglob(ext):
            files.append(file.relative_to(docs_dir))
    return files

def grep(pattern: str, max_results: int = 5):
    """Search for a pattern in all markdown and text files in the document directory.
    Args:        pattern (str): The word or regex pattern to search for.
        max_results (int, optional): The maximum number of results to return. Defaults to 5.
    Returns:        list: A list of strings in the format "relative_path:line_number:line_content"
    """
    docs_dir = get_docs_dir()
    if not docs_dir.exists():
        return []
    results = []
    try:
        rx = re.compile(pattern, re.IGNORECASE)
        # Scan md and txt files
        for ext in ("*.md", "*.txt"):
            for path in docs_dir.rglob(ext):
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, start=1):
                        if rx.search(line):
                            results.append(f"{path.relative_to(docs_dir)}:{i}:{line.rstrip('\n')}")
                            if len(results) >= max_results:
                                return results
        return results
    except Exception as e:
        return [f"Error: {e}"]

def read_slice_doc(path: str, start_line: int, end_line: int):
    """Read a slice of a document in the document directory.
    Args:
        path (str): The path to the document relative to the document directory.
        start_line (int): The starting line number (1-based).
        end_line (int): The ending line number (inclusive).
    Returns:
        str: The content of the specified slice of the document.
    """
    docs_dir = get_docs_dir()
    target = (docs_dir / path).resolve()

    if not target.is_relative_to(docs_dir):
        return "Error: Invalid path. The file must be within the document directory."

    if not target.exists() or not target.is_file():
        return "Error: File not found."

    with open(target, 'r', encoding='utf-8', errors='ignore') as f:
        if end_line is not None:
            chunk = itertools.islice(f, start_line - 1, end_line)
        else:
            chunk = itertools.islice(f, start_line - 1, None)
        return "".join(chunk)

def read_doc(path: str):
    """Read the content of a document in the document directory.
    Args:
        path (str): The path to the document relative to the document directory.
    Returns:
        str: The content of the document.
    """
    docs_dir = get_docs_dir()
    target = (docs_dir / path).resolve()

    if not target.is_relative_to(docs_dir):
        return "Error: Invalid path. The file must be within the document directory."
    
    if not target.is_file():
        return "Error: File not found."
    
    return target.read_text(encoding='utf-8', errors='ignore')


