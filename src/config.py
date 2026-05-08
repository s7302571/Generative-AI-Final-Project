import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent
# Optional convenience location for PDFs the eval harness loads. The Streamlit
# app uploads files directly and never touches this directory.
FILINGS_DIR = ROOT / "data" / "filings"

# Default to Opus 4.7. Override via ASKEDGAR_MODEL if you want to trade
# intelligence for cost (claude-sonnet-4-6) or speed (claude-haiku-4-5).
MODEL = os.getenv("ASKEDGAR_MODEL", "claude-opus-4-7")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
TOP_K = 20
HYBRID_CANDIDATES = 50
RRF_K = 60
CHUNK_TOKENS = 800
CHUNK_OVERLAP = 100
CODE_TIMEOUT_SECONDS = 10
