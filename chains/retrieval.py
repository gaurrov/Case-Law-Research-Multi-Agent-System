"""LangChain retrieval chain — vector store search over case embeddings."""
import yaml
from pathlib import Path
from langchain_chroma import Chroma
from langchain_community.embeddings import SentenceTransformerEmbeddings

_config_path = Path(__file__).parent.parent / "config.yaml"
with open(_config_path) as f:
    _config = yaml.safe_load(f)


def get_vectorstore() -> Chroma:
    embedding_fn = SentenceTransformerEmbeddings(
        model_name=_config["embedding"]["model"]
    )
    return Chroma(
        collection_name="case_chunks",
        persist_directory=_config["embedding"]["chroma_persist_dir"],
        embedding_function=embedding_fn,
    )


def retrieve_candidates(query: str, top_k: int | None = None) -> list[dict]:
    """Retrieve candidate case IDs and snippets from the vector store."""
    if top_k is None:
        top_k = _config["retrieval"]["top_k"]

    vs = get_vectorstore()
    results = vs.similarity_search_with_relevance_scores(query, k=top_k)

    seen_case_ids = set()
    candidates = []
    for doc, score in results:
        case_id = doc.metadata.get("case_id")
        if case_id and case_id not in seen_case_ids:
            seen_case_ids.add(case_id)
            candidates.append({
                "case_id": case_id,
                "snippet": doc.page_content[:300],
                "retrieval_score": round(score, 4),
            })
    return candidates
