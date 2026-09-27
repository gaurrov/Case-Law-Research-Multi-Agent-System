"""Chroma-based vector store for case law embeddings."""
import yaml
from pathlib import Path
from chromadb import PersistentClient
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from db.database import SessionLocal
from db.models import CaseEmbedding

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)

_chroma_dir = _config["embedding"]["chroma_persist_dir"]
_embedding_model = _config["embedding"]["model"]

_client = PersistentClient(path=_chroma_dir)
_ef = SentenceTransformerEmbeddingFunction(model_name=_embedding_model)
collection = _client.get_or_create_collection(
    name="case_chunks",
    embedding_function=_ef,
    metadata={"hnsw:space": "cosine"},
)


def build_index():
    """Load all CaseEmbedding chunks into Chroma (idempotent)."""
    db = SessionLocal()
    try:
        chunks = db.query(CaseEmbedding).all()
        if not chunks:
            print("No embedding chunks found. Run seed_data.py first.")
            return

        existing_ids = set(collection.get()["ids"])
        new_docs, new_ids, new_metas = [], [], []

        for chunk in chunks:
            chroma_id = f"case_{chunk.case_id}_chunk_{chunk.id}"
            if chroma_id in existing_ids:
                continue
            new_docs.append(chunk.chunk_text)
            new_ids.append(chroma_id)
            new_metas.append({"case_id": chunk.case_id, "chunk_id": chunk.id})
            chunk.chroma_id = chroma_id

        if new_docs:
            batch_size = 100
            for i in range(0, len(new_docs), batch_size):
                collection.add(
                    documents=new_docs[i:i + batch_size],
                    ids=new_ids[i:i + batch_size],
                    metadatas=new_metas[i:i + batch_size],
                )
            db.commit()
            print(f"Indexed {len(new_docs)} chunks into Chroma.")
        else:
            print("All chunks already indexed.")
    finally:
        db.close()


def search(query: str, top_k: int = 5) -> list[dict]:
    """Search for relevant case chunks. Returns list of {case_id, chunk_text, score}."""
    results = collection.query(query_texts=[query], n_results=top_k)
    hits = []
    for i in range(len(results["ids"][0])):
        hits.append({
            "case_id": results["metadatas"][0][i]["case_id"],
            "chunk_text": results["documents"][0][i],
            "score": 1.0 - results["distances"][0][i],  # cosine distance -> similarity
        })
    return hits


if __name__ == "__main__":
    build_index()
