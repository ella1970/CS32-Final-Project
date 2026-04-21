"""
ml/rag_pipeline.py

RAG (Retrieval-Augmented Generation) pipeline for clinical rehab protocols.

Two backends supported:
  1. pgvector (PostgreSQL extension) — recommended for production
  2. ChromaDB — easy local dev/test

Switch via RAG_BACKEND env var: "pgvector" | "chroma" (default)

To ingest protocols, run:
    python ml/ingest_protocols.py --dir docs/protocols/
"""
import os
import json
from typing import List

import anthropic

RAG_BACKEND = os.getenv("RAG_BACKEND", "chroma")
client      = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# ── Embedding helper ──────────────────────────────────────────────
def embed_text(text: str) -> List[float]:
    """
    Generate an embedding using Anthropic's embedding endpoint (or OpenAI fallback).
    Currently uses a simple approach — swap in your preferred embedding model.
    """
    # Option A: Use OpenAI embeddings (text-embedding-3-small)
    # import openai
    # resp = openai.embeddings.create(input=text, model="text-embedding-3-small")
    # return resp.data[0].embedding

    # Option B: Use sentence-transformers locally (free, no API key needed)
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        return _model.encode(text).tolist()
    except ImportError:
        raise RuntimeError("Install sentence-transformers: pip install sentence-transformers")


# ── ChromaDB backend ──────────────────────────────────────────────
def _get_chroma_collection():
    import chromadb
    persist_path = os.getenv("CHROMA_PATH", "./chroma_db")
    chroma_client = chromadb.PersistentClient(path=persist_path)
    return chroma_client.get_or_create_collection("rehab_protocols")


def ingest_to_chroma(chunks: List[dict]):
    """
    chunks: list of {"id": str, "text": str, "metadata": dict}
    """
    collection = _get_chroma_collection()
    embeddings = [embed_text(c["text"]) for c in chunks]
    collection.upsert(
        ids        = [c["id"]       for c in chunks],
        documents  = [c["text"]     for c in chunks],
        embeddings = embeddings,
        metadatas  = [c.get("metadata", {}) for c in chunks],
    )
    print(f"Ingested {len(chunks)} chunks to ChromaDB")


def query_chroma(query: str, n_results: int = 3) -> str:
    collection = _get_chroma_collection()
    q_embed = embed_text(query)
    results = collection.query(query_embeddings=[q_embed], n_results=n_results)
    docs = results.get("documents", [[]])[0]
    return "\n---\n".join(docs) if docs else "No relevant protocols found."


# ── pgvector backend ──────────────────────────────────────────────
def ingest_to_pgvector(chunks: List[dict]):
    import psycopg2
    from psycopg2.extras import execute_values
    db_url = os.getenv("DATABASE_URL")
    conn   = psycopg2.connect(db_url)
    cur    = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS protocol_chunks (
            id TEXT PRIMARY KEY,
            content TEXT,
            metadata JSONB,
            embedding vector(384)   -- adjust dim to match your embedding model
        )
    """)
    rows = [
        (c["id"], c["text"], json.dumps(c.get("metadata", {})),
         embed_text(c["text"]))
        for c in chunks
    ]
    execute_values(cur,
        "INSERT INTO protocol_chunks (id, content, metadata, embedding) VALUES %s "
        "ON CONFLICT (id) DO UPDATE SET content=EXCLUDED.content, embedding=EXCLUDED.embedding",
        rows
    )
    conn.commit()
    cur.close(); conn.close()
    print(f"Ingested {len(chunks)} chunks to pgvector")


def query_pgvector(query: str, n_results: int = 3) -> str:
    import psycopg2
    db_url  = os.getenv("DATABASE_URL")
    conn    = psycopg2.connect(db_url)
    cur     = conn.cursor()
    q_embed = embed_text(query)
    cur.execute("""
        SELECT content FROM protocol_chunks
        ORDER BY embedding <-> %s::vector
        LIMIT %s
    """, (q_embed, n_results))
    rows = cur.fetchall()
    cur.close(); conn.close()
    return "\n---\n".join(r[0] for r in rows) if rows else "No relevant protocols found."


# ── Public interface ──────────────────────────────────────────────
def ingest_protocols(chunks: List[dict]):
    if RAG_BACKEND == "pgvector":
        ingest_to_pgvector(chunks)
    else:
        ingest_to_chroma(chunks)


def query_protocols(query: str, n_results: int = 3) -> str:
    if RAG_BACKEND == "pgvector":
        return query_pgvector(query, n_results)
    else:
        return query_chroma(query, n_results)
