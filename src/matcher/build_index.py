"""Build a FAISS index from the supported-sentence CSV.

Reads ``data/supported_set_v1.csv``, embeds all three text variants per row
(english_text, paraphrase_1, paraphrase_2) using the sentence-transformer model
specified in ``config.yaml``, L2-normalises vectors for cosine similarity,
builds a FAISS ``IndexFlatIP`` index and persists it alongside a metadata JSON
that maps each FAISS row position back to its ``sentence_id``.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path

import faiss
import numpy as np
import yaml
from sentence_transformers import SentenceTransformer

# Resolve project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _load_config() -> dict:
    cfg_path = _PROJECT_ROOT / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def build_index() -> None:
    cfg = _load_config()
    model_name: str = cfg["matcher"]["model_name"]
    csv_path = _PROJECT_ROOT / cfg["paths"]["supported_set"]
    index_path = _PROJECT_ROOT / cfg["paths"]["faiss_index"]
    meta_path = _PROJECT_ROOT / cfg["paths"]["index_metadata"]

    # ------------------------------------------------------------------
    # 1. Read the supported-sentence CSV
    # ------------------------------------------------------------------
    text_columns = ["english_text", "paraphrase_1", "paraphrase_2"]
    texts: list[str] = []
    ids: list[str] = []  # parallel list – same length as texts

    with open(csv_path, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            sid = row["sentence_id"]
            for col in text_columns:
                val = row[col].strip()
                if val:
                    texts.append(val)
                    ids.append(sid)

    print(f"Read {len(texts)} text variants from {len(set(ids))} unique sentence_ids")

    # ------------------------------------------------------------------
    # 2. Encode with sentence-transformers
    # ------------------------------------------------------------------
    print(f"Loading model '{model_name}' …")
    model = SentenceTransformer(model_name)
    embeddings: np.ndarray = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)

    # ------------------------------------------------------------------
    # 3. L2-normalise for cosine similarity via inner-product
    # ------------------------------------------------------------------
    faiss.normalize_L2(embeddings)

    # ------------------------------------------------------------------
    # 4. Build and save FAISS IndexFlatIP
    # ------------------------------------------------------------------
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    os.makedirs(index_path.parent, exist_ok=True)
    faiss.write_index(index, str(index_path))
    print(f"FAISS index saved to {index_path} ({index.ntotal} vectors, dim={dim})")

    # ------------------------------------------------------------------
    # 5. Save metadata mapping position → sentence_id
    # ------------------------------------------------------------------
    metadata = {str(i): sid for i, sid in enumerate(ids)}
    os.makedirs(meta_path.parent, exist_ok=True)
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    print(f"Index metadata saved to {meta_path}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    unique_ids = set(ids)
    print(f"\nSummary: {index.ntotal} vectors indexed, {len(unique_ids)} unique sentence_ids")


if __name__ == "__main__":
    build_index()
