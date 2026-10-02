import base64
import hmac
import io
import json
import os
import uuid
from datetime import date
from pathlib import Path

import anthropic
import requests
import streamlit as st
from PIL import Image, ImageOps
from pypdf import PdfReader

# ============================================================
# 1. PATHS + PAGE CONFIG
# ============================================================

BASE_DIR = Path(__file__).parent
IMAGE_PATH = BASE_DIR / "profile.jpg"
PDF_PATH = BASE_DIR / "Sunidhi_Portfolio.pdf"
DATA_FILE = BASE_DIR / "data" / "projects.json"
PROJECT_IMG_DIR = BASE_DIR / "assets" / "projects"

st.set_page_config(page_title="Sunidhi AI", page_icon="✨", layout="wide")


# ============================================================
# 2. SECRETS HELPER (works locally, on Streamlit Cloud, and with env vars)
# ============================================================

def get_secret(name, default=None):
    try:
        return st.secrets[name]
    except Exception:
        return os.environ.get(name, default)


# ============================================================
# 3. STYLING
# ============================================================

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

html, body, .stApp, [class*="css"] { font-family: 'Manrope', 'Segoe UI', sans-serif; }
.stApp { background: #FFFFFF; }
#MainMenu, footer { visibility: hidden; }

/* Sidebar */
[data-testid="stSidebar"] { background: #F8FAFC; border-right: 1px solid #E2E8F0; }
[data-testid="stSidebar"] img {
    border-radius: 50%; width: 150px; height: 150px; object-fit: cover;
    margin: 0 auto; display: block; border: 3px solid #fff;
    box-shadow: 0 0 0 2px #4F46E5;
}
.side-name { text-align: center; font-size: 1.35rem; font-weight: 800; margin: 14px 0 0 0; }
.side-role { text-align: center; font-size: .9rem; color: #475569; margin: 2px 0 10px 0; }
.side-links { text-align: center; margin-bottom: 8px; }
.side-links a { color: #4F46E5 !important; font-weight: 600; text-decoration: none; margin: 0 8px; }
.side-links a:hover { text-decoration: underline; }

/* Hero */
.hero-title { font-size: 2.6rem; font-weight: 800; letter-spacing: -0.03em; line-height: 1.1; margin: 0; }
.hero-sub { color: #475569; font-size: 1.05rem; margin: 10px 0 22px 0; max-width: 60ch; }

/* Chat */
.stChatMessage { background: transparent; border: none; box-shadow: none; }
.stChatMessage:has([data-testid="stChatMessageAvatarUser"]) {
    background: #EEF2FF; border-radius: 18px; padding: 10px 18px; width: fit-content;
    max-width: 80%; margin-left: auto;
}
[data-testid="stChatInput"] { border-radius: 24px; border: 1px solid #CBD5E1; }
[data-testid="stChatInput"]:focus-within { border-color: #4F46E5; }

/* Buttons (suggested questions) */
.stButton > button {
    border-radius: 999px; border: 1px solid #CBD5E1; background: #fff;
    font-weight: 600; padding: .35rem 1rem;
}
.stButton > button:hover { border-color: #4F46E5; color: #4F46E5; }

/* Project cards */
[data-testid="stVerticalBlockBorderWrapper"] { border-radius: 14px; }
.proj-title { font-size: 1.2rem; font-weight: 700; margin: 8px 0 2px 0; }
.proj-date { font-size: .8rem; color: #64748B; margin-bottom: 6px; }
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 4. CLAUDE CLIENT
# ============================================================

ANTHROPIC_API_KEY = get_secret("ANTHROPIC_API_KEY")
MODEL = get_secret("CLAUDE_MODEL", "claude-sonnet-5-5")

if not ANTHROPIC_API_KEY:
    st.error(
        "ANTHROPIC_API_KEY is missing. Add it to `.streamlit/secrets.toml` "
        "(local) or the app's Secrets settings (Streamlit Cloud)."
    )
    st.stop()

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ============================================================
# 5. PORTFOLIO PDF
# ============================================================

@st.cache_data
def extract_portfolio_data():
    if not PDF_PATH.exists():
        return "Portfolio document not found. Ensure Sunidhi_Portfolio.pdf is in the repo."
    try:
        reader = PdfReader(str(PDF_PATH))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        return f"Error reading PDF: {e}"


portfolio_data = extract_portfolio_data()


# ============================================================
# 6. PROJECT STORAGE (repo files; optional auto-commit to GitHub)
# ============================================================

def load_projects():
    try:
        return json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_projects_local(projects):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(projects, indent=2, ensure_ascii=False), encoding="utf-8")


def github_enabled():
    return bool(get_secret("GITHUB_TOKEN") and get_secret("GITHUB_REPO"))


def github_commit(repo_path, content, message):
    """Create/update a file in the GitHub repo. content=None deletes it."""
    repo = get_secret("GITHUB_REPO")
    branch = get_secret("GITHUB_BRANCH", "main")
    headers = {
        "Authorization": f"Bearer {get_secret('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github+json",
    }
    url = f"https://api.github.com/repos/{repo}/contents/{repo_path}"
    r = requests.get(url, headers=headers, params={"ref": branch}, timeout=20)
    sha = r.json().get("sha") if r.status_code == 200 else None

    if content is None:
        if sha:
            requests.delete(
                url, headers=headers, timeout=20,
                json={"message": message, "sha": sha, "branch": branch},
            ).raise_for_status()
        return

    payload = {
        "message": message,
        "content": base64.b64encode(content).decode(),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    requests.put(url, headers=headers, json=payload, timeout=30).raise_for_status()


def process_image(uploaded_file):
    img = ImageOps.exif_transpose(Image.open(uploaded_file)).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=85, optimize=True)
    return buf.getvalue()


def add_project(title, description, files):
    projects = load_projects()
    pid = uuid.uuid4().hex[:8]
    PROJECT_IMG_DIR.mkdir(parents=True, exist_ok=True)

    images = []
    for i, f in enumerate(files):
        data = process_image(f)
        rel = f"assets/projects/{pid}_{i}.jpg"
        (BASE_DIR / rel).write_bytes(data)
        if github_enabled():
            github_commit(rel, data, f"Add image for project: {title}")
        images.append(rel)

    projects.insert(
        0,
        {
            "id": pid,
            "title": title,
            "description": description,
            "images": images,
            "date": date.today().strftime("%b %Y"),
        },
    )
    save_projects_local(projects)
    if github_enabled():
        github_commit(
            "data/projects.json",
            json.dumps(projects, indent=2, ensure_ascii=False).encode(),
            f"Add project: {title}",
        )


def delete_project(pid):
    projects = load_projects()
    target = next((p for p in projects if p["id"] == pid), None)
    if not target:
        return
    for rel in target.get("images", []):
        (BASE_DIR / rel).unlink(missing_ok=True)
        if github_enabled():
            github_commit(rel, None, f"Remove image for project: {target['title']}")
    projects = [p for p in projects if p["id"] != pid]
    save_projects_local(projects)
    if github_enabled():
        github_commit(
            "data/projects.json",
            json.dumps(projects, indent=2, ensure_ascii=False).encode(),
            f"Remove project: {target['title']}",
        )


# ============================================================
# 7. SIDEBAR
# ============================================================

with st.sidebar:
    if IMAGE_PATH.exists():
        st.image(str(IMAGE_PATH))
    st.markdown('<p class="side-name">Sunidhi Rusia</p>', unsafe_allow_html=True)
    st.markdown('<p class="side-role">AI Architect & Data Engineer</p>', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="side-links">
            <a href="https://www.linkedin.com/in/sunidhi-rusia" target="_blank">LinkedIn</a>
            <a href="mailto:sunidhirusia22@gmail.com">Email</a>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**About**")
    st.write(
        "M.S. in Business Analytics & AI at Stevens Institute of Technology. "
        "Specializing in ML, supply chain analytics, and enterprise AI orchestration."
    )
    st.markdown("**Skills**")
    st.write("**AI/ML:** Llama-3.3-70B, Azure OpenAI, Claude API, Prompt Engineering, NLP")
    st.write("**Data:** Python, SQL, Pandas, XGBoost, AWS S3, Supabase")
    with st.expander("Featured projects"):
        st.markdown("- **Athenica Generative AI:** Enterprise Llama-3 deployment.")
        st.markdown("- **StartupHub:** Full-stack talent platform via Claude API.")
        st.markdown("- **Agentic Coach:** Microsoft Copilot Studio system.")


# ============================================================
# 8. HEADER + NAVIGATION
# ============================================================

st.markdown('<h1 class="hero-title">Hi, I\'m Sunidhi AI</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Ask about my experience, skills, and coursework, '
    "or browse the projects I\'ve built.</p>",
    unsafe_allow_html=True,
)

page = st.radio(
    "Section",
    ["Chat", "Projects", "Manage"],
    horizontal=True,
    label_visibility="collapsed",
)


# ============================================================
# 9. CHAT PAGE
# ============================================================

GREETING = (
    "I'm trained on Sunidhi's portfolio, skills, projects, and coursework. "
    "What would you like to know?"
)
SUGGESTIONS = [
    "What projects has Sunidhi built?",
    "Summarize her technical skills",
    "What is her education?",
]


def build_system_prompt():
    projects = load_projects()
    project_text = "\n".join(
        f"- {p['title']} ({p.get('date', '')}): {p['description']}" for p in projects
    ) or "No additional projects have been added yet."

    return f"""You are Sunidhi AI, the interactive professional portfolio assistant for Sunidhi Rusia.

Your source of truth is the portfolio data below.

<portfolio_database>
{portfolio_data}
</portfolio_database>

<additional_projects>
{project_text}
</additional_projects>

Rules:
1. Answer ONLY from the information above. Never invent experience, education, skills, projects, companies, titles, achievements, dates, or technologies.
2. Be concise, professional, and helpful. Use Markdown (short paragraphs, bullets, bold) when it helps.
3. If asked for contact details, give: Email: sunidhirusia22@gmail.com, LinkedIn: https://www.linkedin.com/in/sunidhi-rusia
4. If something isn't covered, say your knowledge is limited to Sunidhi's professional portfolio.
5. You are a portfolio assistant, not a general-purpose assistant.
"""


def stream_reply(messages):
    with client.messages.stream(
        model=MODEL,
        max_tokens=1024,
        system=[
            {
                "type": "text",
                "text": build_system_prompt(),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def render_chat():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.chat_message("assistant", avatar="✨"):
        st.markdown(GREETING)

    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar="✨" if m["role"] == "assistant" else None):
            st.markdown(m["content"])

    if not st.session_state.messages:
        cols = st.columns(len(SUGGESTIONS))
        for col, q in zip(cols, SUGGESTIONS):
            if col.button(q, use_container_width=True):
                st.session_state.pending_prompt = q
                st.rerun()

    prompt = st.chat_input("Ask about Sunidhi...") or st.session_state.pop("pending_prompt", None)
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Claude needs the conversation to start with a user turn; keep last 20 messages
    api_messages = st.session_state.messages[-20:]
    while api_messages and api_messages[0]["role"] != "user":
        api_messages = api_messages[1:]

    with st.chat_message("assistant", avatar="✨"):
        try:
            answer = st.write_stream(stream_reply(api_messages))
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except anthropic.AuthenticationError:
            st.session_state.messages.pop()
            st.error("Claude rejected the API key. Check ANTHROPIC_API_KEY in your secrets.")
        except Exception as e:
            st.session_state.messages.pop()
            st.error(f"Couldn't reach Claude right now.\n\n`{e}`")


# ============================================================
# 10. PROJECTS PAGE
# ============================================================

def render_projects():
    projects = load_projects()
    if not projects:
        st.info("No projects yet. Open **Manage** to add your first one.")
        return

    cols = st.columns(2, gap="large")
    for i, p in enumerate(projects):
        with cols[i % 2]:
            with st.container(border=True):
                imgs = [str(BASE_DIR / r) for r in p.get("images", []) if (BASE_DIR / r).exists()]
                if imgs:
                    st.image(imgs[0])
                st.markdown(f'<div class="proj-title">{p["title"]}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="proj-date">{p.get("date", "")}</div>', unsafe_allow_html=True)
                st.write(p["description"])
                if len(imgs) > 1:
                    with st.expander(f"More photos ({len(imgs) - 1})"):
                        st.image(imgs[1:], width=240)


# ============================================================
# 11. MANAGE PAGE (password protected)
# ============================================================

def render_manage():
    admin_password = get_secret("ADMIN_PASSWORD")
    if not admin_password:
        st.warning("Set ADMIN_PASSWORD in your secrets to enable this section.")
        return

    if not st.session_state.get("admin_ok"):
        pw = st.text_input("Password", type="password")
        if pw and hmac.compare_digest(str(pw), str(admin_password)):
            st.session_state.admin_ok = True
            st.rerun()
        elif pw:
            st.error("Incorrect password.")
        return

    if github_enabled():
        st.caption("Changes are committed to GitHub; the live site redeploys in about a minute.")
    else:
        st.caption(
            "GitHub sync is off, so changes are saved on this machine only. "
            "Commit and push `data/` and `assets/` to publish them."
        )

    st.subheader("Add a project")
    with st.form("add_project", clear_on_submit=True):
        title = st.text_input("Title")
        description = st.text_area("What did you build, and what was the result?", height=140)
        files = st.file_uploader(
            "Pictures", type=["png", "jpg", "jpeg", "webp"], accept_multiple_files=True
        )
        submitted = st.form_submit_button("Save project", type="primary")

    if submitted:
        if not title.strip() or not description.strip():
            st.error("Add a title and a description.")
        else:
            with st.spinner("Saving..."):
                try:
                    add_project(title.strip(), description.strip(), files or [])
                    st.toast("Project saved")
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't save the project: {e}")

    projects = load_projects()
    if projects:
        st.subheader("Your projects")
        for p in projects:
            c1, c2 = st.columns([5, 1])
            c1.write(f"**{p['title']}**  ·  {p.get('date', '')}")
            if c2.button("Delete", key=f"del_{p['id']}"):
                try:
                    delete_project(p["id"])
                    st.rerun()
                except Exception as e:
                    st.error(f"Couldn't delete: {e}")

    if st.button("Log out"):
        st.session_state.admin_ok = False
        st.rerun()


# ============================================================
# 12. ROUTER
# ============================================================

if page == "Chat":
    render_chat()
elif page == "Projects":
    render_projects()
else:
    render_manage()
