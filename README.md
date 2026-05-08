# AskEdgar — AI Analyst for SEC Filings

A RAG + tool-use system that answers questions about SEC 10-K filings. Retrieves relevant passages, generates and executes Python for computations, renders charts when appropriate.

## Setup

Project is managed with [uv](https://docs.astral.sh/uv/). The agent loop runs through the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/), which shells out to the local `claude` CLI — install Claude Code first if you don't have it.

```bash
# 1. Claude Code CLI (one-time, system-wide)
npm install -g @anthropic-ai/claude-code

# 2. Project deps
uv sync
cp .env.example .env  # then edit .env to add ANTHROPIC_API_KEY
```

## Run

```bash
uv run streamlit run app.py
```

Use the upload control in the sidebar to attach a 10-K PDF. Without an upload, the chat runs in general-assistant mode (no RAG, no tool). After uploading, questions are answered against the document and the model can call `run_python` for computations / charts.

## Eval

The eval harness expects PDFs at `data/filings/<filing_id>.pdf`, where `<filing_id>` matches the IDs in `eval/test_set.json` (e.g. `AAPL_10K_2023.pdf`).

```bash
uv run python -m eval.run_eval                # full system + RAG-only baseline
uv run python -m eval.run_eval --system full  # one system only
```

Writes per-question results to `eval/results/`. Scoring against ground truth is left as a TODO in `run_eval.py` — fill it in once the test set has real Q&A pairs.

## Structure

```
app.py                   Streamlit UI (upload + chat + viz)
src/
├── config.py            Model, paths, chunk/retrieval params
├── prompts.py           System prompts (general + filing) + context formatter
├── ingest.py            PDF → text chunks (pure)
├── vectorstore.py       FAISS index built from chunks (in-memory, per upload)
├── tools.py             Sandboxed run_python tool
└── agent.py             Claude Agent SDK loop, optional store + tool
eval/
├── test_set.json        Q&A pairs with ground truth
└── run_eval.py          Compare full vs RAG-only systems
data/filings/            Optional: PDFs the eval harness loads (gitignored)
```

## Notes

- **Sandbox**: `src/tools.py` uses a SIGALRM-based timeout; macOS/Linux only.
- **Model**: defaults to `claude-opus-4-7`. Set `ASKEDGAR_MODEL=claude-sonnet-4-6` in `.env` to trade intelligence for cost.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (free, local). The first run downloads ~80MB to the HF cache.
- **Vector store**: FAISS `IndexFlatIP` over L2-normalized embeddings (cosine similarity). Lives in `st.session_state` only — uploads are not persisted across app restarts.
