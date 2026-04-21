"""
ml/ingest_protocols.py

Ingest clinical rehabilitation protocols into the vector database.

Usage:
    python ml/ingest_protocols.py --dir docs/protocols/
    python ml/ingest_protocols.py --file docs/protocols/slap_repair_protocol.txt

Supported file types: .txt, .pdf, .md

The script chunks documents into ~500 token windows with 50-token overlap,
then embeds and stores them via rag_pipeline.ingest_protocols().
"""
import argparse
import os
import re
import uuid
from pathlib import Path
from typing import List

from rag_pipeline import ingest_protocols


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    """
    Split text into overlapping chunks of approximately chunk_size words.
    """
    words  = text.split()
    chunks = []
    start  = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return chunks


def load_txt(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def load_pdf(path: str) -> str:
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    except ImportError:
        raise RuntimeError("Install pdfplumber: pip install pdfplumber")


def load_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return load_pdf(path)
    else:
        return load_txt(path)


def ingest_directory(directory: str):
    records = []
    for root, _, files in os.walk(directory):
        for fname in files:
            ext = Path(fname).suffix.lower()
            if ext not in (".txt", ".pdf", ".md"):
                continue
            fpath = os.path.join(root, fname)
            print(f"Loading {fpath}...")
            try:
                text   = load_file(fpath)
                chunks = chunk_text(text)
                for i, chunk in enumerate(chunks):
                    records.append({
                        "id":       f"{Path(fname).stem}_{i}",
                        "text":     chunk,
                        "metadata": {"source": fname, "chunk_index": i},
                    })
            except Exception as e:
                print(f"  Skipped ({e})")
    print(f"Ingesting {len(records)} chunks...")
    ingest_protocols(records)
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir",  help="Directory of protocol files")
    parser.add_argument("--file", help="Single protocol file")
    args = parser.parse_args()

    if args.dir:
        ingest_directory(args.dir)
    elif args.file:
        text   = load_file(args.file)
        chunks = chunk_text(text)
        records = [
            {"id": f"{Path(args.file).stem}_{i}", "text": c,
             "metadata": {"source": args.file, "chunk_index": i}}
            for i, c in enumerate(chunks)
        ]
        ingest_protocols(records)
        print(f"Ingested {len(records)} chunks from {args.file}")
    else:
        print("Provide --dir or --file")
