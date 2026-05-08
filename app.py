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
from src.vectorstore import VectorStore

st.set_page_config(page_title="AskEdgar", layout="wide")


def _file_hash(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()[:12]


def _build_store(uploaded_file) -> VectorStore:
    data = uploaded_file.getvalue()
    return VectorStore.from_pdf_bytes(data, name=uploaded_file.name)


def main():
    st.title("AskEdgar — AI Analyst for SEC Filings")

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
                with st.spinner(f"Indexing {uploaded.name}..."):
                    st.session_state.store = _build_store(uploaded)
                    st.session_state.store_hash = new_hash
                    st.session_state.last_figure = None
                st.toast(f"Indexed {uploaded.name} ({len(st.session_state.store)} chunks)")

        if st.session_state.store is not None:
            st.success(f"Loaded: **{st.session_state.store.name}**\n\n{len(st.session_state.store)} chunks indexed")
            if st.button("Remove document", use_container_width=True):
                st.session_state.store = None
                st.session_state.store_hash = None
                st.session_state.last_figure = None
                st.rerun()
        else:
            st.caption("No document loaded — chat is in general mode.")

        st.divider()
        st.caption(f"Model: `{config.MODEL}`")
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.session_state.last_figure = None
            st.rerun()

    chat_col, viz_col = st.columns([3, 2], gap="large")

    with chat_col:
        st.subheader("Chat")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
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

        prompt = st.chat_input("Ask anything — upload a PDF on the left to ground the answer")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
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

    with viz_col:
        st.subheader("Visualization")
        fig = st.session_state.last_figure
        if fig is None:
            st.caption("Charts produced by the model will appear here.")
        else:
            mod = type(fig).__module__
            if mod.startswith("plotly"):
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.pyplot(fig)


if __name__ == "__main__":
    main()
