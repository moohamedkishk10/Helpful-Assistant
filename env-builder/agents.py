import os
import json
from typing import List
import streamlit as st
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_classic.agents import tool
from writer_tools import create_folder, writer_tools, WORKSPACE


def get_api_key():
    try:
        return st.secrets["OPENROUTER_API_KEY"]
    except Exception:
        return os.environ["OPENROUTER_API_KEY"]


llm = ChatOpenAI(
    api_key=get_api_key(),
    base_url="https://openrouter.ai/api/v1",
    model="openai/gpt-4o-mini",
    temperature=0.2
)


class FileSpec(BaseModel):
    path: str = Field(description="relative file path, e.g. app/main.py")
    purpose: str = Field(description="what this file does, in one or two sentences")
    depends_on: List[str] = Field(description="paths of other files in this plan that this file imports or relies on, empty list if none")


PLAN = {}


@tool
def submit_plan(project_name: str, folders: List[str], files: List[FileSpec], dependencies: List[str]) -> str:
    "submit the final project architecture: project name, all folders, all files (each with path, purpose, depends_on), and python dependencies"
    PLAN["project_name"] = project_name
    PLAN["folders"] = folders
    PLAN["files"] = [f.model_dump() if hasattr(f, "model_dump") else f for f in files]
    PLAN["dependencies"] = dependencies
    return "Plan submitted successfully."


writer_agent = create_agent(
    model=llm,
    tools=writer_tools,
    system_prompt=(
        "You are a senior software engineer. "
        "You build project environments on disk using your tools. "
        "Write every file with complete, working code. "
        "Do not leave placeholders or TODOs. "
        "Use read_file to check any file you depend on before writing a file that imports from it. "
        "The project plan uses paths relative to the project root. "
        "The project root folder name is NOT part of any Python import: "
        "if the plan has app/calculator.py, import it as app.calculator, never as <project_name>.app.calculator. "
        "When calling your tools, use the exact tool paths given in the task."
    ),
)

planner_agent = create_agent(
    model=llm,
    tools=[submit_plan],
    system_prompt=(
        "You are a senior software architect. "
        "The user describes a project. Design its full architecture and then "
        "call the submit_plan tool exactly once with the complete plan. "
        "Every file must have a path, a purpose, and depends_on (paths of other files in the plan it imports). "
        "Every path in depends_on must also exist in the files list. "
        "depends_on must reflect real Python imports: a file lists the files it imports from, never the reverse. "
        "Entry points like app/main.py depend on the modules they load. "
        "Config files are depended on by the modules that use them. "
        "Always include these engineering files in the plan: "
        "Dockerfile, .dockerignore, .github/workflows/ci.yml, requirements.txt, "
        ".gitignore, .env.example, README.md, a tests/ folder with at least one test file, "
        "and a config file for the app. "
        "Organize the code by responsibility (separate UI, models, utils, config). "
        "Do not write any code. Only plan."
    ),
)


def get_write_order(plan):
    files = {f["path"]: f for f in plan["files"]}
    ordered = []
    visited = set()
    visiting = set()

    def visit(path):
        if path in visited:
            return
        if path in visiting:
            raise ValueError(f"Circular dependency at {path}")
        visiting.add(path)
        for dep in files[path]["depends_on"]:
            if dep in files:
                visit(dep)
        visiting.remove(path)
        visited.add(path)
        ordered.append(files[path])

    for path in files:
        visit(path)

    return ordered


def build_project(user_request):
    PLAN.clear()
    planner_agent.invoke({
        "messages": [{"role": "user", "content": user_request}]
    })

    if not PLAN:
        raise RuntimeError("Planner did not submit a plan")

    project_dir = PLAN["project_name"].strip().replace(" ", "_").lower()
    PLAN["project_dir"] = project_dir

    for folder in PLAN["folders"]:
        create_folder.invoke({"path": f"{project_dir}/{folder}"})

    plan_text = json.dumps(
        {
            "project_name": PLAN["project_name"],
            "dependencies": PLAN["dependencies"],
            "folders": PLAN["folders"],
            "files": PLAN["files"],
        },
        indent=2,
    )

    for f in get_write_order(PLAN):
        print("Writing:", f["path"])
        tool_path = f"{project_dir}/{f['path']}"
        tool_deps = [f"{project_dir}/{d}" for d in f["depends_on"]]
        task = (
            f"Project plan (all paths are relative to the project root):\n{plan_text}\n\n"
            f"Write ONLY this file: {f['path']}\n"
            f"Purpose: {f['purpose']}\n\n"
            f"Tool paths: when you call write_file, use the path: {tool_path}\n"
            f"When you call read_file on the files it depends on, use these paths: {tool_deps}\n\n"
            "Python imports must follow the plan paths, starting from the project root "
            f"(for example app/calculator.py is imported as app.calculator). "
            f"Never put '{project_dir}' inside an import. "
            "If this file depends on other files, call read_file on each of them first "
            "and use their real function and class names. "
            "Then call write_file once with the complete content of this file."
        )
        writer_agent.invoke({"messages": [{"role": "user", "content": task}]})

    print("Done. Check the workspace folder.")