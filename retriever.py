"""ChromaDB-backed document storage and retrieval for Corpus Forge."""

from typing import Any, Dict, List, Optional

import chromadb

_client: Optional[Any] = None
_collection = None


def init_chroma():
    """Initialize a local ChromaDB client and create the `corpus` collection."""
    global _client, _collection

    if _client is None:
        _client = chromadb.PersistentClient(path="chroma_db")

    _collection = _client.get_or_create_collection(name="corpus")
    return _collection


def _get_collection():
    if _collection is None:
        return init_chroma()
    return _collection


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if not text:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be greater than or equal to 0 and smaller than chunk_size"
        )

    chunks: List[str] = []
    step = chunk_size - overlap
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += step

    return chunks


def add_document(doc_id: str, text: str, filename: str):
    """Split `text` into chunks and store them in ChromaDB."""
    collection = _get_collection()
    chunks = _chunk_text(text, chunk_size=500, overlap=50)

    if not chunks:
        return

    ids = [f"{doc_id}_{index}" for index in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "filename": filename, "chunk_index": index}
        for index in range(len(chunks))
    ]

    collection.add(ids=ids, documents=chunks, metadatas=metadatas)


def _extract_query_results(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])
    distances = result.get("distances", [])
    ids = result.get("ids", [])

    if not documents:
        return []

    docs = documents[0] if documents and isinstance(documents[0], list) else documents
    metas = metadatas[0] if metadatas and isinstance(metadatas[0], list) else metadatas
    dists = distances[0] if distances and isinstance(distances[0], list) else distances
    query_ids = ids[0] if ids and isinstance(ids[0], list) else ids

    extracted: List[Dict[str, Any]] = []
    for index, document in enumerate(docs):
        extracted.append(
            {
                "id": query_ids[index] if index < len(query_ids) else None,
                "document": document,
                "metadata": metas[index] if index < len(metas) else {},
                "distance": dists[index] if index < len(dists) else None,
            }
        )
    return extracted


def query(question: str, doc_ids: List[str], n_results: int = 3) -> str:
    """Return the most relevant chunks for `question` from only `doc_ids`."""
    collection = _get_collection()

    if not doc_ids or n_results <= 0:
        return ""

    ranked_results: List[Dict[str, Any]] = []

    for doc_id in doc_ids:
        result = collection.query(
            query_texts=[question],
            n_results=n_results,
            where={"doc_id": doc_id},
            include=["documents", "metadatas", "distances"],
        )
        ranked_results.extend(_extract_query_results(result))

    ranked_results = [item for item in ranked_results if item["document"]]
    ranked_results.sort(
        key=lambda item: (
            item["distance"] if item["distance"] is not None else float("inf")
        )
    )

    top_documents = [item["document"] for item in ranked_results[:n_results]]
    return "\n\n".join(top_documents)


def delete_document(doc_id: str):
    """Remove all chunks belonging to `doc_id` from ChromaDB."""
    collection = _get_collection()
    result = collection.get(where={"doc_id": doc_id})
    ids = result.get("ids", [])

    if ids:
        collection.delete(ids=ids)
