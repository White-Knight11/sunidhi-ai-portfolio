import json
import os
from pathlib import Path

import streamlit as st
from google import genai
from google.genai import errors, types
from pypdf import PdfReader

# ============================================================
# 1. PATHS + PAGE CONFIG
# ============================================================

BASE_DIR = Path(__file__).parent
IMAGE_PATH = BASE_DIR / "profile.jpg"
PDF_PATH = BASE_DIR / "Sunidhi_Portfolio.pdf"
DATA_FILE = BASE_DIR / "data" / "projects.json"

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

</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# 4. GEMINI CLIENT
# ============================================================

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
MODEL = get_secret("GEMINI_MODEL", "gemini-2.5-flash")

if not GEMINI_API_KEY:
    st.error(
        "GEMINI_API_KEY is missing. Add it to `.streamlit/secrets.toml` "
        "(local) or the app's Secrets settings (Streamlit Cloud)."
    )
    st.stop()

client = genai.Client(api_key=GEMINI_API_KEY)


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
# 6. PROJECT DATA (read-only)
# ============================================================

def load_projects():
    if not DATA_FILE.exists():
        return []
    try:
        projects = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Project data in {DATA_FILE} is not valid JSON.") from e
    if not isinstance(projects, list):
        raise ValueError(f"Project data in {DATA_FILE} must be a JSON array.")
    return projects


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


# ============================================================
# 8. HEADER + NAVIGATION
# ============================================================

st.markdown('<h1 class="hero-title">Hi, I\'m Sunidhi AI</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">Ask about my experience, skills, projects, and coursework.</p>',
    unsafe_allow_html=True,
)

page = "Chat"



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
    contents = [
        types.Content(
            role="model" if message["role"] == "assistant" else "user",
            parts=[types.Part.from_text(text=message["content"])],
        )
        for message in messages
    ]
    for chunk in client.models.generate_content_stream(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            max_output_tokens=1024,
        ),
    ):
        if chunk.text:
            yield chunk.text


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

    # Gemini conversations must begin with a user turn; keep the last 20 messages
    api_messages = st.session_state.messages[-20:]
    while api_messages and api_messages[0]["role"] != "user":
        api_messages = api_messages[1:]

    with st.chat_message("assistant", avatar="✨"):
        try:
            answer = st.write_stream(stream_reply(api_messages))
            st.session_state.messages.append({"role": "assistant", "content": answer})
        except errors.APIError as e:
            st.session_state.messages.pop()
            st.error(f"Gemini API error: {e}")
        except Exception as e:
            st.session_state.messages.pop()
            st.error(f"Couldn't reach Gemini right now.\n\n`{e}`")


# ============================================================


# ============================================================
# 10. CHAT ROUTER
# ============================================================

render_chat()
