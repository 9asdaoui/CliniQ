import streamlit as st
import requests
import json

# ── Config ──────────────────────────────────────────────────────────────────
API_BASE = "http://backend:8000"

st.set_page_config(
    page_title="CliniQ",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ───────────────────────────────────────────────────
SUGGESTED_QUESTIONS = [
    "Quel est le traitement d'une laryngite chez l'enfant ?",
    "Quelles sont les recommandations générales pour l'usage des antibiotiques ?",
    "Comment prendre en charge une douleur abdominale chez l'enfant ?",
    "Quel est le traitement en cas de piqûre de poisson pierre ?",
    "Comment gérer une difficultè respiratoire chez le nourrisson ?",
    "Quels sont les signes d'une infection cutanée nécessitant des antibiotiques IV ?",
    "Quelle est la conduite à tenir en cas de morsure ou envenimation ?",
    "Quand faut-il changer de palier antalgique chez l'enfant ?",
]

for key, default in {
    "token": None,
    "first_name": "",
    "last_name": "",
    "role": "",
    "messages": [],
    "pending_query": "",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ──────────────────────────────────────────────────────────────────
def auth_headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def logout():
    for key in ["token", "first_name", "last_name", "role", "messages"]:
        st.session_state[key] = [] if key == "messages" else None if key == "token" else ""
    st.rerun()


# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        /* global palette */
        :root {
            --primary: #2563EB;
            --primary-dark: #1D4ED8;
            --surface: #F8FAFC;
            --card: #FFFFFF;
            --accent: #10B981;
            --danger: #EF4444;
            --text: #1E293B;
            --muted: #64748B;
        }

        /* hide default streamlit header/footer */
        #MainMenu, footer, header {visibility: hidden;}

        /* top nav bar */
        .topbar {
            background: linear-gradient(90deg, #1E3A5F 0%, #2563EB 100%);
            padding: 14px 32px;
            border-radius: 0 0 12px 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            color: white;
            margin-bottom: 20px;
        }
        .topbar h1 {margin: 0; font-size: 1.6rem; font-weight: 700;}
        .topbar span {font-size: 0.9rem; opacity: 0.85;}

        /* chat bubbles */
        .chat-user {
            background: #EFF6FF;
            border-left: 4px solid #2563EB;
            padding: 10px 16px;
            border-radius: 8px;
            margin: 8px 0;
            color: #1E293B !important;
        }
        .chat-bot {
            background: #F0FDF4;
            border-left: 4px solid #10B981;
            padding: 10px 16px;
            border-radius: 8px;
            margin: 8px 0;
            color: #1E293B !important;
        }
        .chat-user *, .chat-bot * {
            color: #1E293B !important;
        }
        .chat-label {
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }
        .user-label {color: #2563EB !important;}
        .bot-label  {color: #059669 !important;}

        /* auth card */
        .auth-card {
            max-width: 420px;
            margin: 60px auto;
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.08);
        }

        /* upload zone */
        .upload-hint {
            font-size: 0.82rem;
            color: var(--muted);
            text-align: center;
            margin-top: 6px;
        }

        /* suggestion chips */
        .chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 16px 0 8px 0;
        }
        .chip {
            background: #EFF6FF;
            border: 1.5px solid #BFDBFE;
            color: #1D4ED8 !important;
            padding: 6px 14px;
            border-radius: 99px;
            font-size: 0.82rem;
            cursor: pointer;
            transition: all .15s;
            white-space: nowrap;
        }
        .chip:hover { background:#DBEAFE; border-color:#93C5FD; }

        /* pill badge */
        .badge {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 99px;
            font-size: 0.75rem;
            font-weight: 600;
        }
        .badge-user  {background:#DBEAFE; color:#1D4ED8 !important;}
        .badge-admin {background:#FEF3C7; color:#B45309 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


# ════════════════════════════════════════════════════════════════════════════
#  AUTH PAGE
# ════════════════════════════════════════════════════════════════════════════
def auth_page():
    st.markdown(
        """
        <div style='text-align:center; margin-top:30px; margin-bottom:8px;'>
            <span style='font-size:3rem;'>🩺</span>
            <h1 style='margin:0; color:#1E3A5F; font-size:2.2rem; font-weight:800;'>CliniQ</h1>
            <p style='color:#64748B; font-size:1rem;'>AI-Powered Clinical Knowledge Assistant</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_left, col_center, col_right = st.columns([1, 2, 1])
    with col_center:
        login_tab, register_tab = st.tabs(["🔐 Login", "📝 Register"])

        # ── Login tab ──
        with login_tab:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="doctor@clinic.com")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button(
                    "Login", use_container_width=True, type="primary"
                )

            if submitted:
                if not email or not password:
                    st.warning("Please fill in all fields.")
                else:
                    with st.spinner("Authenticating…"):
                        try:
                            resp = requests.post(
                                f"{API_BASE}/auth/login",
                                json={"email": email, "password": password},
                                timeout=30,
                            )
                        except requests.exceptions.ReadTimeout:
                            st.error("Backend is taking too long to respond. Please try again.")
                            return
                        except requests.exceptions.ConnectionError:
                            st.error("Cannot reach the backend. Make sure the server is running.")
                            return

                    if resp.status_code == 200:
                        data = resp.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.first_name = data["first_name"]
                        st.session_state.last_name = data["last_name"]
                        st.session_state.role = data["role"]
                        st.success("Welcome back!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Please try again.")

        # ── Register tab ──
        with register_tab:
            with st.form("register_form"):
                col1, col2 = st.columns(2)
                with col1:
                    first_name = st.text_input("First Name")
                with col2:
                    last_name = st.text_input("Last Name")
                reg_email = st.text_input("Email", placeholder="doctor@clinic.com", key="reg_email")
                reg_password = st.text_input(
                    "Password",
                    type="password",
                    help="Minimum 8 characters",
                    key="reg_pass",
                )
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm")
                reg_submitted = st.form_submit_button(
                    "Create Account", use_container_width=True, type="primary"
                )

            if reg_submitted:
                if not all([first_name, last_name, reg_email, reg_password, reg_confirm]):
                    st.warning("Please fill in all fields.")
                elif reg_password != reg_confirm:
                    st.error("Passwords do not match.")
                elif len(reg_password) < 8:
                    st.error("Password must be at least 8 characters.")
                else:
                    with st.spinner("Creating account…"):
                        try:
                            resp = requests.post(
                                f"{API_BASE}/auth/register",
                                json={
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "email": reg_email,
                                    "password": reg_password,
                                },
                                timeout=30,
                            )
                        except requests.exceptions.ReadTimeout:
                            st.error("Backend is taking too long to respond. Please try again.")
                            return
                        except requests.exceptions.ConnectionError:
                            st.error("Cannot reach the backend.")
                            return

                    if resp.status_code == 201:
                        data = resp.json()
                        st.session_state.token = data["access_token"]
                        st.session_state.first_name = data["first_name"]
                        st.session_state.last_name = data["last_name"]
                        st.session_state.role = data["role"]
                        st.success("Account created! Welcome to CliniQ.")
                        st.rerun()
                    elif resp.status_code == 409:
                        st.error("An account with this email already exists.")
                    else:
                        st.error(f"Registration failed: {resp.text}")


# ════════════════════════════════════════════════════════════════════════════
#  MAIN APP (authenticated)
# ════════════════════════════════════════════════════════════════════════════
def main_app():
    badge_cls = "badge-admin" if st.session_state.role == "ADMIN" else "badge-user"

    # ── Top bar ──
    st.markdown(
        f"""
        <div class='topbar'>
            <h1>🩺 CliniQ</h1>
            <span>
                {st.session_state.first_name} {st.session_state.last_name}&nbsp;
                <span class='badge {badge_cls}'>{st.session_state.role}</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Sidebar ──
    with st.sidebar:
        st.markdown("### 📂 Knowledge Base")
        st.markdown("Upload a clinical document to add it to the knowledge base.")

        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "docx"],
            label_visibility="collapsed",
        )
        st.markdown(
            "<p class='upload-hint'>Supported: PDF · TXT · DOCX</p>",
            unsafe_allow_html=True,
        )

        if uploaded_file and st.button("📤 Ingest Document", use_container_width=True, type="primary"):
            with st.spinner("Processing document…"):
                try:
                    resp = requests.post(
                        f"{API_BASE}/rag/ingest",
                        files={"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)},
                        timeout=120,
                    )
                except requests.exceptions.ConnectionError:
                    st.error("Cannot reach the backend.")
                    resp = None

            if resp and resp.status_code == 200:
                data = resp.json()
                st.success("Document ingested successfully!")
                st.info(
                    f"**Parent chunks:** {data.get('Parent Chunks Count', '–')}  \n"
                    f"**Child chunks:** {data.get('Child Chunks Count', '–')}"
                )
            elif resp:
                st.error(f"Ingestion failed: {resp.text}")

        st.divider()
        st.markdown("### ⚙️ Session")
        if st.button("🚪 Logout", use_container_width=True):
            logout()

    # ── Chat interface ──
    st.markdown("#### 💬 Ask CliniQ")
    st.caption("Ask a clinical question and get an evidence-based answer from the knowledge base.")

    # ── Suggested questions (shown only when chat is empty) ──
    if not st.session_state.messages:
        st.markdown("<p style='font-size:0.83rem;color:#64748B;margin-bottom:4px;'>💡 Try one of these:</p>", unsafe_allow_html=True)
        cols = st.columns(2)
        for i, q in enumerate(SUGGESTED_QUESTIONS):
            if cols[i % 2].button(q, key=f"sug_{i}", use_container_width=True):
                st.session_state.pending_query = q
                st.rerun()

    # Render existing messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f"<div class='chat-user'>"
                    f"<div class='chat-label user-label'>You</div>"
                    f"{msg['content']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='chat-bot'>"
                    f"<div class='chat-label bot-label'>CliniQ</div>"
                    f"{msg['content']}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # Query input
    with st.form("query_form", clear_on_submit=True):
        col_input, col_btn = st.columns([6, 1])
        with col_input:
            query = st.text_input(
                "Query",
                value=st.session_state.pending_query,
                placeholder="e.g. What are the contraindications of metformin?",
                label_visibility="collapsed",
            )
        with col_btn:
            send = st.form_submit_button("Send", type="primary", use_container_width=True)

    # auto-send when a suggestion chip was clicked
    if st.session_state.pending_query and not send:
        send = True
        query = st.session_state.pending_query
    st.session_state.pending_query = ""

    if send and query.strip():
        st.session_state.messages.append({"role": "user", "content": query.strip()})

        with st.spinner("Searching knowledge base and generating answer…"):
            try:
                resp = requests.post(
                    f"{API_BASE}/rag/generate",
                    json={"query": query.strip()},
                    headers=auth_headers(),
                    timeout=300,
                )
            except requests.exceptions.ReadTimeout:
                st.session_state.messages.append({"role": "assistant", "content": "⏳ The model is taking too long to respond (CPU inference is slow). Please try again or ask a shorter question."})
                st.rerun()
                resp = None
            except requests.exceptions.ConnectionError:
                st.session_state.messages.append({"role": "assistant", "content": "❌ Cannot reach the backend. Make sure the server is running."})
                st.rerun()
                resp = None

        if resp is None:
            pass
        elif resp.status_code == 200:
            data = resp.json()
            answer = (
                data.get("answer")
                or data.get("response")
                or data.get("result")
                or json.dumps(data, indent=2)
            )
            st.session_state.messages.append({"role": "assistant", "content": answer})
            st.rerun()
        elif resp.status_code == 401:
            st.session_state.messages.pop()
            logout()
        elif resp.status_code == 404:
            st.session_state.messages.append({"role": "assistant", "content": "⚠️ The knowledge base is empty. Please upload and ingest a document using the sidebar first."})
            st.rerun()
        else:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            st.session_state.messages.append({"role": "assistant", "content": f"❌ Error {resp.status_code}: {detail}"})
            st.rerun()

    # Clear chat
    if st.session_state.messages:
        if st.button("🗑️ Clear conversation"):
            st.session_state.messages = []
            st.rerun()


# ════════════════════════════════════════════════════════════════════════════
#  Router
# ════════════════════════════════════════════════════════════════════════════
if st.session_state.token:
    main_app()
else:
    auth_page()
