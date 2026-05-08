"""AskEdgar Streamlit app."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from src import config
from src.agent import ask
from src.ingest import ingest_filing, list_filings

st.set_page_config(page_title="AskEdgar", layout="wide")


@st.cache_resource
def _bootstrap_filings() -> list[str]:
    """Ingest any PDFs in data/filings/ that haven't been indexed yet."""
    indexed = set(list_filings())
    config.FILINGS_DIR.mkdir(parents=True, exist_ok=True)
    for pdf in config.FILINGS_DIR.glob("*.pdf"):
        filing_id = pdf.stem
        if filing_id not in indexed:
            with st.spinner(f"Indexing {pdf.name}..."):
                n = ingest_filing(pdf, filing_id)
                st.toast(f"Indexed {pdf.name} ({n} chunks)")
    return list_filings()


def main():
    st.title("AskEdgar — AI Analyst for SEC Filings")

    filings = _bootstrap_filings()
    if not filings:
        st.warning(
            f"No filings indexed. Drop a 10-K PDF into `{config.FILINGS_DIR}` and reload."
        )
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_figure" not in st.session_state:
        st.session_state.last_figure = None

    with st.sidebar:
        st.header("Filing")
        filing_id = st.selectbox("Select 10-K", filings)
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
                            st.text(c["text"][:1500] + ("..." if len(c["text"]) > 1500 else ""))
                if msg.get("tool_calls"):
                    for j, tc in enumerate(msg["tool_calls"], 1):
                        with st.expander(f"Code (call {j})"):
                            st.code(tc["code"], language="python")
                            if tc["stdout"]:
                                st.text(tc["stdout"])
                            if tc["error"]:
                                st.error(tc["error"])

        prompt = st.chat_input("Ask a question about the filing...")
        if prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    resp = ask(prompt, filing_id, enable_tool=True)
                st.markdown(resp.answer)
                # Persist for re-render
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
