"""AskEdgar Streamlit app.

Two modes:
- No PDF uploaded: plain chat with the Claude Agent SDK.
- PDF uploaded: RAG over a FAISS index built from that PDF, plus run_python.
"""

from __future__ import annotations

# Silence the noisy `[transformers] Accessing __path__ from ...` deprecation
# spam that fires when transformers lazy-loads its image-processing registry.
# Must be set BEFORE any transformers/sentence-transformers import.
import os
import warnings

os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TRANSFORMERS_NO_ADVISORY_WARNINGS", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
warnings.filterwarnings("ignore", message=r".*Accessing __path__.*")
warnings.filterwarnings("ignore", message=r".*image_processing.*")

import hashlib

import streamlit as st

from src import config
from src.agent import ask
from src.ingest import PDFTextExtractionError
from src.vectorstore import VectorStore

st.set_page_config(page_title="AskEdgar", layout="wide")


# Sidebar-as-chat styling: widen the sidebar and tighten chat bubbles inside it.
CHAT_CSS = """
<style>
/* === Wider sidebar so chat has room === */
[data-testid="stSidebar"] {
    min-width: 420px !important;
    max-width: 520px !important;
}

/* === Message bubbles === */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border: none !important;
    padding: 4px 0 !important;
    margin-bottom: 4px !important;
    box-shadow: none !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    flex-direction: row-reverse;
    margin-left: auto;
    max-width: 90%;
    background: #ffffff !important;
    border: 1px solid #e3e3e6 !important;
    border-radius: 16px !important;
    padding: 8px 12px !important;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) > div:last-child {
    text-align: left;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    max-width: 100%;
    padding: 4px 0 !important;
}
[data-testid="stChatMessageAvatarUser"],
[data-testid="stChatMessageAvatarAssistant"] {
    width: 26px !important;
    height: 26px !important;
    min-width: 26px !important;
    font-size: 13px !important;
}
[data-testid="stChatMessage"] p {
    margin-bottom: 0;
    line-height: 1.5;
}

/* === Chat input in the sidebar === */
[data-testid="stSidebar"] [data-testid="stChatInput"] {
    border: 1.5px solid #e0e0e0 !important;
    border-radius: 14px !important;
    background: #ffffff !important;
    margin-top: 8px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}
[data-testid="stSidebar"] [data-testid="stChatInput"]:focus-within {
    border-color: #e0e0e0 !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}
/* Also strip the inner textarea's focus outline/border. */
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea:focus,
[data-testid="stSidebar"] [data-testid="stChatInput"] textarea:focus-visible {
    outline: none !important;
    box-shadow: none !important;
    border-color: transparent !important;
}

/* Lock the sidebar to the viewport — no outer scrolling. The chat history
   inside flex-grows and scrolls internally; the input sits at the bottom. */
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    height: calc(100vh - 3.5rem) !important;
    max-height: calc(100vh - 3.5rem) !important;
    overflow: hidden !important;
    display: flex !important;
    flex-direction: column !important;
}
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] > div:first-child,
[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
    height: 100% !important;
    min-height: 0 !important;
    display: flex !important;
    flex-direction: column !important;
}
/* Chat history fills remaining vertical space and scrolls internally */
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] {
    height: auto !important;
    flex: 1 1 auto !important;
    min-height: 200px !important;
    overflow: auto !important;
}
/* Belt-and-suspenders: also pin the chat input to the bottom */
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > [data-testid="element-container"]:has([data-testid="stChatInput"]),
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] > div:has(> [data-testid="stChatInput"]) {
    margin-top: auto !important;
    flex: 0 0 auto !important;
}
</style>
"""

EMPTY_STATE_HTML = """
<div style="
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #999;
    text-align: center;
    padding: 60px 20px;
">
    <div style="font-size: 44px; margin-bottom: 16px;">💬</div>
    <div style="font-size: 18px; font-weight: 500; color: #555;">Ask me anything</div>
    <div style="font-size: 13px; margin-top: 8px;">
        Upload a PDF on the left to ground answers in a document.
    </div>
</div>
"""


def _file_hash(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def _build_store(uploaded_file) -> VectorStore:
    data = uploaded_file.getvalue()
    return VectorStore.from_pdf_bytes(data, name=uploaded_file.name)


def main():
    st.markdown(CHAT_CSS, unsafe_allow_html=True)
    st.markdown(
        "<h1 style='text-align: center;'>AskEdgar — AI Analyst for SEC Filings</h1>",
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_figure" not in st.session_state:
        st.session_state.last_figure = None
    if "store" not in st.session_state:
        st.session_state.store = None
    if "store_hash" not in st.session_state:
        st.session_state.store_hash = None

    with st.sidebar:
        st.header("Document")
        uploaded = st.file_uploader("Upload a PDF (e.g. a 10-K)", type=["pdf"])

        if uploaded is not None:
            data = uploaded.getvalue()
            new_hash = _file_hash(data)
            if st.session_state.store_hash != new_hash:
                try:
                    with st.spinner(f"Indexing {uploaded.name}..."):
                        st.session_state.store = _build_store(uploaded)
                        st.session_state.store_hash = new_hash
                        st.session_state.last_figure = None
                    st.toast(f"Indexed {uploaded.name} ({len(st.session_state.store)} chunks)")
                except PDFTextExtractionError as e:
                    st.error(str(e))
                    st.session_state.store = None
                    st.session_state.store_hash = None
                    st.stop()
                except Exception as e:
                    st.error(f"Indexing failed: {e}")
                    st.session_state.store = None
                    st.session_state.store_hash = None
                    st.stop()

        if st.session_state.store is not None:
            st.success(f"Loaded: **{st.session_state.store.name}**\n\n{len(st.session_state.store)} chunks indexed")
            btn_remove, btn_clear = st.columns([1, 1])
            if btn_remove.button("Remove document", use_container_width=True):
                st.session_state.store = None
                st.session_state.store_hash = None
                st.session_state.last_figure = None
                st.rerun()
            if btn_clear.button("Clear chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.last_figure = None
                st.rerun()
        else:
            st.caption("No document loaded — chat is in general mode.")
            if st.button("Clear chat", use_container_width=True):
                st.session_state.messages = []
                st.session_state.last_figure = None
                st.rerun()

        st.divider()

        # Chat history scrolls inside the sidebar; CSS sizes it to fill remaining space
        history = st.container(height=420, border=False)
        with history:
            if not st.session_state.messages:
                st.markdown(EMPTY_STATE_HTML, unsafe_allow_html=True)
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🤖"):
                    st.markdown(msg["content"])
                    if msg.get("chunks"):
                        with st.expander(f"Sources ({len(msg['chunks'])} passages)"):
                            for i, c in enumerate(msg["chunks"], 1):
                                st.markdown(f"**[{i}] {c['section']} · p.{c['page']}**")
                                preview = c["text"][:1500] + ("..." if len(c["text"]) > 1500 else "")
                                st.text(preview)
                    if msg.get("tool_calls"):
                        for j, tc in enumerate(msg["tool_calls"], 1):
                            with st.expander(f"Code (call {j})"):
                                st.code(tc["code"], language="python")
                                if tc["stdout"]:
                                    st.text(tc["stdout"])
                                if tc["error"]:
                                    st.error(tc["error"])

        prompt = st.chat_input("Ask anything — upload a PDF above to ground the answer")

    # Main area: visualization only
    st.markdown(
        "<h3 style='text-align: center;'>Visualization</h3>",
        unsafe_allow_html=True,
    )
    fig = st.session_state.last_figure
    if fig is not None:
        mod = type(fig).__module__
        if mod.startswith("plotly"):
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.pyplot(fig)

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with history:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Thinking..."):
                    resp = ask(
                        prompt,
                        store=st.session_state.store,
                        enable_tool=st.session_state.store is not None,
                    )
                st.markdown(resp.answer)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": resp.answer,
                "chunks": resp.chunks,
                "tool_calls": [
                    {
                        "code": tc.code,
                        "stdout": tc.result.stdout,
                        "error": tc.result.error,
                    }
                    for tc in resp.tool_calls
                ],
            }
        )
        if resp.figure is not None:
            st.session_state.last_figure = resp.figure
        st.rerun()


if __name__ == "__main__":
    main()
