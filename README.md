# AskEdgar — AI Analyst for SEC 10-K Filings

A small RAG + tool-use app that answers quantitative questions about a single SEC 10-K filing. Upload one PDF, ask a question in natural language, get a cited answer — and, when the question needs arithmetic, the model writes and runs Python in a sandbox so the number is computed, not guessed.

## 1. User and workflow

**User:** an equity-research analyst, finance student, or investor who needs to extract numbers and ratios from a specific 10-K.

**Workflow it replaces:** open the PDF, Ctrl-F for the line item, copy figures into a spreadsheet, compute the ratio, write a short answer with citations.

**Scope:** one filing at a time, one quantitative question at a time. The app does not browse the web, does not compare across filings, does not give investment advice.

## 2. What I built

A Streamlit app (`app.py`) plus a callable agent (`src/agent.py`) usable by the eval harness or any Python caller.

- PDF → text chunks (`src/ingest.py`) with section/page metadata.
- FAISS index over MiniLM embeddings, built in-memory per upload (`src/vectorstore.py`).
- Single LLM call via the Claude Agent SDK that retrieves top-K passages, then optionally calls a sandboxed `run_python` MCP tool (`src/tools.py`) for arithmetic or charts.
- Structured `<answer_json>` block in the model output so a programmatic grader can read the answer without parsing prose.

That's the whole system: retrieval + one tool. No multi-agent loop, no cross-document RAG, no fine-tuning.

## 3. Why GenAI is useful here

10-Ks are long (100+ pages), heavily tabular, and inconsistently formatted. Three things the model does that a baseline doesn't:

1. **Locates the right number** in prose like "Total net sales increased 6% during 2025 ..." or in tables that pdfplumber turns into noisy text.
2. **Interprets the question** — "operating margin" maps to operating income / total net sales without the user having to spell out the formula.
3. **Computes exactly** via the Python tool when arithmetic is non-trivial (CAGR, HHI, sample SD, DuPont decomposition).

A keyword-search baseline can do (1) on simple lookups but fails on (2) and (3). A pure-prompt baseline does (1) and (2) but is unreliable on (3) for multi-step math.

## 4. Baseline comparison

The eval harness runs the **full system** (RAG + `run_python`) against a **RAG-only baseline** (same retrieval, same prompt, tool disabled). Both use the same model so the only variable is the tool.

Test set: 23 questions on Apple's FY2025 10-K (`eval/test_set.json`) — 7 simple ratios/growth rates and 16 multi-step calculations (CAGR, HHI, working capital, DuPont ROE, sample SD).

Grading: numeric answers are matched against ground truth within a per-question tolerance (`eval/grader.py`). The model emits a structured `<answer_json>` block so grading is mechanical, not LLM-judged.

Latest run (`eval/results/report.md`):

| System | Accuracy | Avg latency | Output tokens | Cost | Tool calls |
|---|---|---|---|---|---|
| **full** (RAG + Python) | 23/23 (100%) | 15.75s | 18,477 | $1.39 | 9 |
| **rag_only** (baseline) | 23/23 (100%) | 13.54s | 16,605 | $1.25 | 0 |

## 5. What worked, what failed, where a human stays in

**Worked**
- Retrieval reliably surfaced the right income-statement / balance-sheet rows. Both systems grounded on the correct numbers across all 23 questions.
- The `<answer_json>` contract eliminated brittle regex parsing in the grader — every response was parseable.
- Sandboxed `run_python` produced exact arithmetic on the 9 questions where the model chose to call it.

**Failed / surprising**
- **The tool didn't change accuracy on this test set.** Opus 4.7 did the arithmetic in its head correctly even on CAGR, HHI, and sample SD. The tool added latency (~16% slower) and cost (~11% more) without lifting accuracy from 100%. The tool would matter more on (a) longer arithmetic chains where mental math drifts, (b) chart requests, (c) smaller models — none of which this test set exercises.
- **One filing, one company.** The eval doesn't test cross-filing comparison, non-Apple formatting quirks, or filings where the relevant number lives in a footnote outside the top-K retrieved chunks. Generalization beyond Apple is unverified.
- **No adversarial questions.** Ground-truth-free / unanswerable questions aren't in the test set, so I can't claim the model abstains correctly when the document doesn't contain the answer.

**Where a human stays in**
- Verify the cited passage actually supports the claim — retrieval can return a plausible-looking but wrong section.
- For anything forward-looking ("guidance", "risk factors"), treat the answer as a starting point, not a conclusion.
- For investment decisions, the system is a research assistant, not an analyst of record.

## 6. Setup

Project is managed with [uv](https://docs.astral.sh/uv/). The agent loop runs through the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/), which shells out to the local `claude` CLI — install Claude Code first if you don't have it.

```bash
# 1. Claude Code CLI (one-time, system-wide)
npm install -g @anthropic-ai/claude-code

# 2. Project deps
uv sync
cp .env.example .env  # then edit .env to add ANTHROPIC_API_KEY
```

`.env` must contain `ANTHROPIC_API_KEY=sk-ant-...`. Optional: `ASKEDGAR_MODEL=claude-sonnet-4-6` to swap the default `claude-opus-4-7`.

## 7. Run the app

```bash
uv run streamlit run app.py
```

Use the upload control in the sidebar to attach a 10-K PDF. Without an upload, the chat runs in general-assistant mode (no RAG, no tool). After uploading, questions are answered against the document and the model can call `run_python` for computations / charts.

## 8. Reproduce the eval

The eval harness expects PDFs at `data/filings/<filing_id>.pdf`, where `<filing_id>` matches the IDs in `eval/test_set.json` (e.g. `AAPL-2025.pdf`).

The pipeline has three stages, each writing to `eval/results/` with fixed filenames (every run overwrites the previous):

| Stage | Command | Output |
| --- | --- | --- |
| 1. Run models (calls API) | `uv run python -m eval.run_eval` | `full.json`, `rag_only.json` |
| 2. Grade vs. ground truth | `uv run python -m eval.grader` | `graded_full.json`, `graded_rag_only.json` |
| 3. Aggregate into report | `uv run python -m eval.aggregate` | `report.md` |

One-shot all three stages:

```bash
uv run python -m eval.pipeline                # full system + RAG-only baseline
uv run python -m eval.pipeline --system full  # one system only
```

Run stages individually when iterating on the grader/report without re-spending API credits — Stage 2 and Stage 3 read the JSON written by Stage 1, so you can re-grade and re-aggregate as many times as you want for free:

```bash
uv run python -m eval.run_eval     # Stage 1 only — re-runs models
uv run python -m eval.grader       # Stage 2 only — re-grades existing results
uv run python -m eval.aggregate    # Stage 3 only — rebuilds report.md
```

## 9. Repo layout

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
├── run_eval.py          Stage 1 — runs full + rag_only systems
├── grader.py            Stage 2 — grades structured answers vs. ground truth
├── aggregate.py         Stage 3 — builds report.md
├── pipeline.py          Runs all three stages
└── results/             Generated JSON + report.md
data/filings/            PDFs the eval harness loads (gitignored)
```

## 10. Notes

- **Sandbox**: `src/tools.py` uses a SIGALRM-based timeout; macOS/Linux only.
- **Model**: defaults to `claude-opus-4-7`. Set `ASKEDGAR_MODEL=claude-sonnet-4-6` in `.env` to trade intelligence for cost.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (free, local). The first run downloads ~80MB to the HF cache.
- **Vector store**: FAISS `IndexFlatIP` over L2-normalized embeddings (cosine similarity). Lives in `st.session_state` only — uploads are not persisted across app restarts.
- **No secrets in repo**: `.env` is gitignored; `.env.example` shows the required key without a value.
