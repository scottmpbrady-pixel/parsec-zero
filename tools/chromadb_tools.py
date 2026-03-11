"""
ChromaDB vector memory tools for CrewAI agents.

Provides persistent cross-session memory:
- Designers embed specs so Developers can query them
- QA embeds error logs to avoid repeating fixes
- Project Manager queries history to avoid contradictions
"""
import os
from typing import Optional

import chromadb
from crewai.tools import tool
from dotenv import load_dotenv

load_dotenv()

CHROMADB_PATH = os.getenv("CHROMADB_PATH", "memory/chromadb")

# Collections
COLLECTION_DESIGN = "design_documents"
COLLECTION_ERRORS = "error_logs"
COLLECTION_DECISIONS = "architectural_decisions"

_client: Optional[chromadb.PersistentClient] = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMADB_PATH)
    return _client


def _get_collection(name: str) -> chromadb.Collection:
    client = _get_client()
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


@tool("Embed design document into agent memory")
def embed_design_document(doc_id: str, title: str, content: str) -> str:
    """
    Embed a design document into ChromaDB for cross-session memory.
    The Systems Designer calls this after writing any spec.
    All other agents can later query this memory to stay consistent.

    Args:
        doc_id: Unique identifier (e.g. "level_1_spec", "player_stats_v2")
        title: Human-readable title
        content: The full document text to embed

    Returns confirmation string.
    """
    collection = _get_collection(COLLECTION_DESIGN)
    collection.upsert(
        ids=[doc_id],
        documents=[content],
        metadatas=[{"title": title, "doc_id": doc_id}],
    )
    return f"OK: Embedded design document '{doc_id}' into memory."


@tool("Query design documents from agent memory")
def query_design_memory(query: str, n_results: int = 3) -> str:
    """
    Query ChromaDB for design documents relevant to a question.
    Use this before writing any code or spec to check for existing decisions.

    Examples:
        query_design_memory("What is the player HP?")
        query_design_memory("Enemy stats for level 1")
        query_design_memory("How does movement work?")

    Returns the top matching document excerpts.
    """
    collection = _get_collection(COLLECTION_DESIGN)
    results = collection.query(query_texts=[query], n_results=n_results)

    if not results["documents"] or not results["documents"][0]:
        return "No relevant design documents found in memory."

    output_parts = []
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0]), start=1
    ):
        title = meta.get("title", "Untitled")
        output_parts.append(f"[{i}] {title}\n{doc[:800]}")

    return "\n\n---\n\n".join(output_parts)


@tool("Embed error log into agent memory")
def embed_error_log(error_id: str, context: str, error_text: str, fix_applied: str = "") -> str:
    """
    Embed a Godot build error and its fix into ChromaDB.
    The QA agent calls this after resolving each error.
    Future QA runs query this to avoid repeating the same fix.

    Args:
        error_id: Unique ID (e.g. "err_player_gd_2026_03_10_001")
        context: Which file/feature was being built
        error_text: The raw error output from Godot
        fix_applied: What fix was applied (or empty if unresolved)

    Returns confirmation string.
    """
    collection = _get_collection(COLLECTION_ERRORS)
    doc = f"CONTEXT: {context}\n\nERROR:\n{error_text}\n\nFIX:\n{fix_applied}"
    collection.upsert(
        ids=[error_id],
        documents=[doc],
        metadatas={"error_id": error_id, "context": context, "resolved": bool(fix_applied)},
    )
    return f"OK: Embedded error log '{error_id}' into memory."


@tool("Query past error logs from agent memory")
def query_error_history(error_description: str, n_results: int = 3) -> str:
    """
    Query ChromaDB for similar past errors and their fixes.
    The QA agent calls this before attempting a fix to check if we've seen it before.

    Args:
        error_description: Description or excerpt of the current error

    Returns the top matching past errors with their fixes.
    """
    collection = _get_collection(COLLECTION_ERRORS)
    results = collection.query(query_texts=[error_description], n_results=n_results)

    if not results["documents"] or not results["documents"][0]:
        return "No similar errors found in history. This appears to be a new error type."

    output_parts = []
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0]), start=1
    ):
        output_parts.append(f"[{i}] Past error (ID: {meta.get('error_id', 'unknown')})\n{doc[:1000]}")

    return "\n\n---\n\n".join(output_parts)
