import io
import os
import copy
import zipfile
import threading
import streamlit as st
import streamlit.components.v1 as components
from agents import PLAN, build_project, WORKSPACE

st.set_page_config(page_title="Environment Builder", layout="wide")

st.markdown("""
<style>
.stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
    background: #D6C7AE !important;
}
.stApp h1, .stApp h2, .stApp h3, .stApp p, .stApp label, .stApp span,
.stApp li, .stApp div[data-testid="stMarkdownContainer"] {
    color: #1F1A14 !important;
}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p {
    color: #5C5242 !important;
}
div[data-baseweb="textarea"], div[data-baseweb="base-input"] {
    background: #EFE6D4 !important;
    border: 1px solid #B8A98C !important;
    border-radius: 10px !important;
}
textarea {
    background: #EFE6D4 !important;
    color: #1F1A14 !important;
    -webkit-text-fill-color: #1F1A14 !important;
}
textarea::placeholder {
    color: #7A6E5A !important;
    -webkit-text-fill-color: #7A6E5A !important;
}
.stButton > button[kind="primary"], .stDownloadButton > button {
    background: #0891B2 !important;
    border: none !important;
    border-radius: 10px !important;
}
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] span,
.stDownloadButton > button p, .stDownloadButton > button span {
    color: #FFFFFF !important;
}
[data-testid="stTable"] table, [data-testid="stTable"] th, [data-testid="stTable"] td {
    background: transparent !important;
    color: #1F1A14 !important;
    border-color: #B8A98C !important;
}
</style>
""", unsafe_allow_html=True)

LOGO_HTML = """
<style>body{margin:0;background:transparent}</style>
<div style="margin:0;padding:0;background:#050508;border-radius:16px;display:flex;align-items:center;justify-content:center;height:200px;overflow:hidden;font-family:'Inter',sans-serif;">
  <style>
    .wordmark{font-size:56px;font-weight:700;letter-spacing:-2px;display:inline-flex;align-items:baseline;direction:ltr}
    .wm-K{color:#e2e8f0;font-weight:900;opacity:0;animation:revUp .7s ease .2s forwards}
    .wm-e{font-weight:300;color:#06b6d4;margin-left:-3px;opacity:0;animation:revUp .7s ease .3s forwards}
    .wm-Y{font-weight:900;color:#06b6d4;opacity:0;animation:revUp .7s ease .4s forwards}
    .s-wrap{position:relative;display:inline-block;width:52px;height:78px;margin:0 6px;vertical-align:baseline;opacity:0;animation:revUp .7s ease .5s forwards}
    .s-top{position:absolute;top:0;left:0;width:100%;height:42%;overflow:hidden;font-size:56px;font-weight:700;line-height:1;color:#1e40af;clip-path:polygon(0 0,100% 0,100% 70%,0 100%)}
    .s-top::before{content:'S';position:absolute;top:0;left:0}
    .s-bot{position:absolute;bottom:0;left:0;width:100%;height:42%;overflow:hidden;font-size:56px;font-weight:700;line-height:1;color:#0d9488;clip-path:polygon(0 30%,100% 0,100% 100%,0 100%)}
    .s-bot::before{content:'S';position:absolute;bottom:0;left:0}
    .glow-line{position:absolute;top:50%;left:0;width:100%;height:2px;background:linear-gradient(90deg,transparent,rgba(6,182,212,.9),rgba(20,184,166,.9),transparent);transform:translateY(-50%);animation:glowPulse 2s ease-in-out infinite}
    .the-key{position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:70px;height:20px;opacity:0;animation:keySlide 1s cubic-bezier(.34,1.56,.64,1) .7s forwards}
    .key-head{position:absolute;left:0;top:50%;transform:translateY(-50%);width:20px;height:20px;border:3px solid #06b6d4;border-radius:50%;background:rgba(6,182,212,.15);box-shadow:0 0 20px rgba(6,182,212,.4)}
    .key-shaft{position:absolute;left:38%;top:50%;transform:translateY(-50%);width:50%;height:5px;background:linear-gradient(90deg,#06b6d4,#14b8a6,#06b6d4);border-radius:4px;box-shadow:0 0 18px rgba(6,182,212,.5)}
    .key-teeth{position:absolute;right:0;top:50%;transform:translateY(-50%);display:flex;gap:2px;align-items:flex-end}
    .key-teeth span{display:block;width:5px;background:linear-gradient(180deg,#14b8a6,#06b6d4);border-radius:0 0 2px 2px}
    .key-teeth span:nth-child(1){height:10px} .key-teeth span:nth-child(2){height:16px}
    .key-teeth span:nth-child(3){height:7px} .key-teeth span:nth-child(4){height:13px}
    .wm-h{font-weight:600;color:#06b6d4;margin-left:-3px;opacity:0;animation:revUp .7s ease .85s forwards}
    .wm-k{font-weight:900;color:#e2e8f0;opacity:0;animation:revUp .7s ease 1s forwards}
    .tagline{display:block;text-align:center;margin-top:18px;font-size:10px;letter-spacing:8px;text-transform:uppercase;color:#334155;opacity:0;animation:revUp .6s ease 1.2s forwards}
    @keyframes revUp{0%{opacity:0;transform:translateY(24px)}100%{opacity:1;transform:none}}
    @keyframes keySlide{0%{opacity:0;transform:translate(-140%,-50%) scale(.7)}100%{opacity:1;transform:translate(-50%,-50%) scale(1)}}
    @keyframes glowPulse{0%,100%{opacity:.4}50%{opacity:1}}
  </style>
  <div style="text-align:center">
    <div class="wordmark">
      <span class="wm-K">K</span><span class="wm-e">e</span><span class="wm-Y">Y</span>
      <div class="s-wrap">
        <div class="s-top"></div><div class="glow-line"></div><div class="s-bot"></div>
        <div class="the-key"><div class="key-head"></div><div class="key-shaft"></div>
          <div class="key-teeth"><span></span><span></span><span></span><span></span></div>
        </div>
      </div>
      <span class="wm-h">h</span><span class="wm-k">k</span>
    </div>
    <span class="tagline">Key Check Tech</span>
  </div>
</div>
"""


@st.cache_resource
def get_lock():
    return threading.Lock()


def make_zip(project_root, plan_files):
    buf = io.BytesIO()
    existing = []
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in plan_files:
            full = os.path.join(project_root, f["path"])
            if os.path.exists(full):
                z.write(full, arcname=f["path"])
                existing.append(f["path"])
    return buf.getvalue(), existing


components.html(LOGO_HTML, height=200)

st.title("Environment Builder")
st.caption("Describe your project. The planner designs the architecture and the writer builds it on disk.")

request = st.text_area(
    "Describe your project",
    height=150,
    placeholder="Let's build",
)

if st.button("Build", type="primary"):
    if not request.strip():
        st.warning("Write a project description first.")
    else:
        with st.spinner("Planning and writing files..."):
            with get_lock():
                build_project(request)
                plan = copy.deepcopy(PLAN)
                project_root = os.path.join(WORKSPACE, plan["project_dir"])
                zip_bytes, existing = make_zip(project_root, plan["files"])
        st.session_state["result"] = {
            "project_dir": plan["project_dir"],
            "files": plan["files"],
            "zip": zip_bytes,
            "existing": existing,
        }

result = st.session_state.get("result")

if result:
    st.success("Done")

    st.download_button(
        "Download project (ZIP)",
        data=result["zip"],
        file_name=f"{result['project_dir']}.zip",
        mime="application/zip",
    )

    st.subheader("Plan")
    st.table([
        {"path": f["path"], "purpose": f["purpose"], "depends_on": ", ".join(f["depends_on"])}
        for f in result["files"]
    ])

    st.subheader("Files written")
    for path in result["existing"]:
        st.text(path)