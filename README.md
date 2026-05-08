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

Drop one or more 10-K PDFs into `data/filings/` (filename = `<TICKER>_10K_<YEAR>.pdf` is the convention used by the eval test set).

## Run

```bash
uv run streamlit run app.py
```

The app auto-indexes any new PDFs on startup.

## Eval

```bash
uv run python -m eval.run_eval                # full system + RAG-only baseline
uv run python -m eval.run_eval --system full  # one system only
```

Writes per-question results to `eval/results/`. Scoring against ground truth is left as a TODO in `run_eval.py` — fill it in once the test set has real Q&A pairs.

## Structure

```
app.py                   Streamlit UI
src/
├── config.py            Model, paths, chunk/retrieval params
├── prompts.py           System prompt + retrieved-context formatter
├── ingest.py            PDF → chunks → embeddings → ChromaDB
├── retrieve.py          Vector search
├── tools.py             Sandboxed run_python tool
└── agent.py             LLM loop with tool use
eval/
├── test_set.json        Q&A pairs with ground truth
└── run_eval.py          Compare full vs RAG-only systems
data/filings/            Drop PDFs here (gitignored)
data/index/              ChromaDB persistent store (gitignored)
```

## Notes

- **Sandbox**: `src/tools.py` uses a SIGALRM-based timeout; macOS/Linux only.
- **Model**: defaults to `claude-opus-4-7`. Set `ASKEDGAR_MODEL=claude-sonnet-4-6` in `.env` to trade intelligence for cost.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (free, local). The first run downloads ~80MB to the HF cache.
