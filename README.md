# AskEdgar — AI Analyst for SEC 10-K Filings

A small RAG + tool-use app that answers quantitative questions about a single SEC 10-K filing. Upload one PDF, ask a question in natural language, get a cited answer — and, when the question needs arithmetic, the model writes and runs Python in a sandbox so the number is computed, not guessed.

<img width="2510" height="1347" alt="image" src="https://github.com/user-attachments/assets/3ca16a70-aa74-4811-8324-3f611e7b3b72" />

## 1. Context, user, and problem

**User.** An equity-research analyst, finance student, or individual investor — someone who reads one 10-K at a time to answer a specific quantitative question (a margin, a growth rate, a ratio) with a citation they can defend in a model or report.

**Workflow it replaces.** Today the same task is a 5–10 minute manual loop: open the 100+ page PDF, Ctrl-F the line item, copy figures into Excel, compute the ratio by hand, write a short cited answer.

**Why it matters.** 10-Ks are long, dense, and inconsistently formatted (prose mixed with tables that PDF extractors mangle). Each lookup is slow and error-prone, and the mistakes propagate downstream into valuation models and reports. The goal is to turn a 10-minute manual lookup into a single natural-language question with a cited, computed answer.

**Scope.** One filing at a time, one quantitative question at a time. The app does not browse the web, does not compare across filings, does not give investment advice.

## 2. Solution and design

A Streamlit app (`app.py`) plus a callable agent (`src/agent.py`) usable by the eval harness or any Python caller. The pipeline is six stages, end to end:

```
PDF upload → ingest → hybrid retrieval → LLM call → (optional) run_python → answer
```

- **PDF → text chunks** with section/page metadata (`src/ingest.py`, pdfplumber).
- **Hybrid retrieval** built in-memory per upload (`src/vectorstore.py`): dense MiniLM embeddings (FAISS `IndexFlatIP` over L2-normalized vectors) **+** BM25 sparse, fused with **Reciprocal Rank Fusion**. Catches both paraphrased prose ("net sales rose 6%") and exact line items in tables — neither retriever alone is enough on noisy 10-K text.
- **Single LLM call** via the Claude Agent SDK with a "use ONLY these passages" prompt (`src/prompts.py`).
- **Optional `run_python` tool** in an MCP sandbox (`src/tools.py`) that the model invokes for arithmetic or charts — the number is computed, not guessed.
- **Structured `<answer_json>` block** in every response so a programmatic grader (or any downstream caller) can read the answer mechanically — no LLM-as-judge, no brittle regex.

That's the whole system: retrieval + one optional tool. No multi-agent loop, no cross-document RAG, no fine-tuning. The design choices that matter:

1. **Hybrid retrieval** — RRF avoids having to calibrate score scales across the two retrievers.
2. **Tool use, not mental math** — when the question needs CAGR, ratios, or a chart, the model writes Python and runs it in a sandbox.
3. **Structured output contract** — `<answer_json>` makes evaluation mechanical and reuse trivial.
4. **One agent, one call** — complexity has to earn its keep; this version does the job.

### Why GenAI is the right tool

Three things the model does that a non-LLM baseline doesn't:

1. **Locates the right number** in prose ("Total net sales increased 6% during 2025 …") or in tables that pdfplumber turns into noisy text.
2. **Interprets the question** — "operating margin" maps to operating income / total net sales without the user having to spell out the formula.
3. **Computes exactly** via the Python tool on multi-step math (CAGR, HHI, sample SD, DuPont decomposition).

A keyword-search baseline can do (1) on simple lookups but fails on (2) and (3). A pure-prompt baseline does (1) and (2) but is unreliable on (3) for multi-step math.

## 3. Evaluation and results

**What we tested.** 23 questions on Apple's FY2025 10-K (`eval/test_set.json`) — 7 simple lookups and 16 multi-step calculations (CAGR, HHI, working capital, DuPont ROE, sample SD).

**What we compared against.** The full system (RAG + `run_python`) vs. a **RAG-only baseline** with the same retrieval and same prompt but with the tool disabled. Only variable: the tool. Run on **two models** — Opus 4.7 and Haiku 4.5 — to test whether the tool's value depends on model strength.

**How we graded.** Numeric answers are matched against ground truth within a per-question tolerance (`eval/grader.py`), reading the structured `<answer_json>` block from each response. Grading is mechanical, not LLM-judged.

### Two runs, one story

**Opus 4.7 — tool: redundant**

| System | Accuracy | Avg latency | Cost | Tool calls |
|---|---|---|---|---|
| **full** (RAG + Python) | 23/23 (100%) | 15.75 s | $1.39 | 9 |
| **rag_only** (baseline) | 23/23 (100%) | 13.54 s | $1.25 | 0 |

Δ = 0 accuracy gain · +16% latency · +11% cost — Opus did the arithmetic in its head.

**Haiku 4.5 — tool: decisive**

| System | Accuracy | Avg latency | Tool calls |
|---|---|---|---|
| **full** (RAG + Python) | 23/23 (100%) | 12.45 s | 19 |
| **rag_only** (baseline) | 21/23 (91%) | 12.38 s | 0 |

Δ = +9 pp accuracy. The tool fixed two silent arithmetic slips the smaller model would otherwise have shipped:

- `AAPL-2025-simple-07`: 13.51 → 14.0 (rounding drift)
- `AAPL-2025-complex-11`: 42.86% → 0.4286 (decimal-vs-percent error on a segment-share calculation)

The latest run (`eval/results/report.md`) is the Haiku run; the Opus run is summarized above.

### Headline finding

**Tool value scales inversely with model strength — it's a cost lever, not just an accuracy lever.** Haiku + `run_python` matches Opus's 100% accuracy at roughly one-tenth the cost. The tool moves the cost-quality frontier rather than just plugging accuracy holes on a single model.

### What worked, what failed, where a human stays in

**Worked**
- Hybrid retrieval reliably surfaced the right income-statement / balance-sheet rows. Both systems grounded on the correct numbers across both models.
- The `<answer_json>` contract eliminated brittle regex parsing in the grader — every response was parseable.
- Sandboxed `run_python` produced exact arithmetic on every call and replaced the silent rounding / decimal-vs-% drifts that Haiku otherwise made.

**Failed / surprising**
- **On Opus, the tool didn't move accuracy.** Opus 4.7 did CAGR, HHI, and sample SD in its head and the tool only added ~16% latency and ~11% cost. The lesson is to pick model first, then architect — same workflow has different optimal architectures across models.
- **One filing, one company.** The eval doesn't test cross-filing comparison, non-Apple formatting quirks, or filings where the relevant number lives in a footnote outside the top-K retrieved chunks. Generalization beyond Apple is unverified.
- **No adversarial questions.** Ground-truth-free / unanswerable questions aren't in the test set, so I can't claim the model abstains correctly when the document doesn't contain the answer.

**Where a human stays in**
- Verify the cited passage actually supports the claim — retrieval can return a plausible-looking but wrong section.
- For anything forward-looking ("guidance", "risk factors"), treat the answer as a starting point, not a conclusion.
- For investment decisions, the system is a research assistant, not an analyst of record.

## Artifact snapshot
<img width="526" height="290" alt="image" src="https://github.com/user-attachments/assets/944c570a-d79c-4d12-b43d-2c710cc4193d" />
Q: Plot Apple FY2025 revenue by geographic segment. 

LLM:  Pulls Item 7 segment table, generates a labeled bar chart in-app via run_python.

<img width="526" height="272" alt="image" src="https://github.com/user-attachments/assets/63fc0186-19f9-4116-8bae-3a85fcb6ae7a" />
Q: How did each product line change? 

LLM: diverging bar chart with Services leading at +$12.99B and Wearables declining $1.32B. Grounded to disaggregated revenue table.

## 4. Setup

Project is managed with [uv](https://docs.astral.sh/uv/). The agent loop runs through the [Claude Agent SDK](https://pypi.org/project/claude-agent-sdk/), which shells out to the local `claude` CLI — install Claude Code first if you don't have it.

```bash
# 1. Claude Code CLI (one-time, system-wide)
npm install -g @anthropic-ai/claude-code

# 2. Project deps
uv sync
cp .env.example .env  # then edit .env to add ANTHROPIC_API_KEY
```

Optional: `ASKEDGAR_MODEL=claude-sonnet-4-6` or `claude-opus-4-7` to swap the default `claude-haiku-4-5`.

Note: If you're already authenticated with Claude Code locally (e.g., via claude login), you don't need to set ANTHROPIC_API_KEY in .env. The Claude Agent SDK shells out to the local claude CLI and will reuse its existing login session.

## 5. Run the app

```bash
uv run streamlit run app.py
```

Use the upload control in the sidebar to attach a 10-K PDF. Without an upload, the chat runs in general-assistant mode (no RAG, no tool). After uploading, questions are answered against the document and the model can call `run_python` for computations / charts.

## 6. Reproduce the eval

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

## 7. Repo layout

```
app.py                   Streamlit UI (upload + chat + viz)
src/
├── config.py            Model, paths, chunk/retrieval params
├── prompts.py           System prompts (general + filing) + context formatter
├── ingest.py            PDF → text chunks (pure)
├── vectorstore.py       Hybrid retrieval (FAISS dense + BM25 sparse + RRF), in-memory per upload
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

## 8. Notes

- **Sandbox**: `src/tools.py` uses a SIGALRM-based timeout; macOS/Linux only.
- **Model**: defaults to `claude-haiku-4-5` — the eval shows Haiku + `run_python` matches Opus on this task at a fraction of the cost. Set `ASKEDGAR_MODEL=claude-sonnet-4-6` or `claude-opus-4-7` in `.env` to swap.
- **Embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (free, local). The first run downloads ~80MB to the HF cache.
- **Retrieval**: hybrid — dense (FAISS `IndexFlatIP` over L2-normalized MiniLM embeddings, cosine similarity) + sparse (BM25Okapi over lowercased tokens), fused with Reciprocal Rank Fusion. Lives in `st.session_state` only — uploads are not persisted across app restarts.
- **No secrets in repo**: `.env` is gitignored; `.env.example` shows the required key without a value.
