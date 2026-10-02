import os
from langchain_classic.agents import tool

WORKSPACE = os.path.abspath("workspace")
os.makedirs(WORKSPACE, exist_ok=True)


def _safe_path(relative_path: str) -> str:
    full = os.path.abspath(os.path.join(WORKSPACE, relative_path))
    if not full.startswith(WORKSPACE + os.sep) and full != WORKSPACE:
        raise ValueError(f"Path is outside the workspace: {relative_path}")
    return full


@tool
def create_folder(path: str) -> str:
    "create a folder inside the workspace by giving its relative path, e.g. app/pages"
    full = _safe_path(path)
    os.makedirs(full, exist_ok=True)
    return f"Folder created: {path}"


@tool
def write_file(path: str, content: str) -> str:
    "write a file inside the workspace by giving its relative path and its full content"
    full = _safe_path(path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)
    return f"File written: {path}"


@tool
def read_file(path: str) -> str:
    "read a file from the workspace by giving its relative path"
    full = _safe_path(path)
    if not os.path.exists(full):
        return f"File not found: {path}"
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


writer_tools = [create_folder, write_file, read_file]