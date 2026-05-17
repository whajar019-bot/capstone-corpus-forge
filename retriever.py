"""ChromaDB-backed document retriever for Corpus Forge.

Provides:
- init_chroma() -> initializes a local ChromaDB client and collection 'corpus'
- add_document(doc_id, text, filename) -> chunk text and add chunks with metadata
- query(question, doc_ids, n_results=3) -> retrieve top-matching chunks for given doc_ids
- delete_document(doc_id) -> delete all chunks belonging to a document

This module uses only the `chromadb` library for storage. A lightweight text
ranking is applied locally (difflib) to pick the most relevant chunks.
"""
from typing import List, Optional
import chromadb
from difflib import SequenceMatcher

# Module-level client and collection
_client: Optional[chromadb.Client] = None
_collection = None


def init_chroma(persist_directory: Optional[str] = None):
    """Initialize a local ChromaDB client and ensure a collection named 'corpus'.

    If `persist_directory` is provided, it will be passed to ChromaDB Settings
    so data can be persisted locally.
    """
    global _client, _collection

    # Create client (try to pass Settings if available)
    try:
        # Preferred: use Settings to allow a persist directory if provided
        Settings = getattr(chromadb.config, "Settings", None)
        if Settings is not None:
            settings = Settings(persist_directory=persist_directory) if persist_directory else Settings()
            _client = chromadb.Client(settings=settings)
        else:
            _client = chromadb.Client()
    except Exception:
        # Fallback to simple constructor
        _client = chromadb.Client()

    # Get or create the collection named 'corpus'
    try:
        if hasattr(_client, "get_or_create_collection"):
            _collection = _client.get_or_create_collection(name="corpus")
        elif hasattr(_client, "get_collection"):
            # get_collection will raise if missing; create if necessary
            try:
                _collection = _client.get_collection(name="corpus")
            except Exception:
                _collection = _client.create_collection(name="corpus")
        else:
            # Last resort: try create_collection
            _collection = _client.create_collection(name="corpus")
    except Exception:
        # Re-raise with helpful context
        raise


def _ensure_client():
    if _client is None or _collection is None:
        raise RuntimeError("ChromaDB client not initialized. Call init_chroma() first.")


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    chunks: List[str] = []
    start = 0
    step = chunk_size - overlap
    text_len = len(text)
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= text_len:
            break
        start += step
    return chunks


def add_document(doc_id: str, text: str, filename: str):
    """Split `text` into chunks and add them to the 'corpus' collection.

    Each chunk is 500 characters with 50 characters overlap. Metadata stored:
    `{ 'doc_id': doc_id, 'filename': filename }`.
    """
    _ensure_client()

    chunks = _chunk_text(text, chunk_size=500, overlap=50)
    if not chunks:
        return

    ids = [f"{doc_id}_chunk_{i}" for i in range(len(chunks))]
    metadatas = [{"doc_id": doc_id, "filename": filename} for _ in chunks]

    # Use collection.add; argument names vary slightly between chroma versions
    try:
        _collection.add(ids=ids, documents=chunks, metadatas=metadatas)
    except TypeError:
        # some versions expect (documents=..., metadatas=..., ids=...)
        _collection.add(documents=chunks, metadatas=metadatas, ids=ids)


def query(question: str, doc_ids: List[str], n_results: int = 3) -> str:
    """Search for the most relevant chunks among `doc_ids` and return combined text.

    This function retrieves candidate chunks for the provided `doc_ids` from
    ChromaDB, ranks them by simple text similarity to `question`, and returns
    the top `n_results` chunks concatenated into a single string.
    """
    _ensure_client()

    # Collect candidates from ChromaDB for each doc_id
    candidate_texts = []
    candidate_ids = []
    for did in doc_ids:
        # Try to fetch items with metadata filter; API differs across versions
        try:
            res = _collection.get(where={"doc_id": did})
        except Exception:
            # Fallback: try query() with metadata filter
            try:
                res = _collection.query(query_texts=[question], where={"doc_id": did}, n_results=100, include=["documents", "ids"])
                # query() returns dict-like results; unify below
            except Exception:
                # As a last resort, skip this doc_id
                continue

        # Normalize result structure
        ids = res.get("ids") if isinstance(res, dict) else None
        docs = res.get("documents") if isinstance(res, dict) else None
        if ids is None or docs is None:
            # Some versions return lists directly
            try:
                ids = res["ids"]
                docs = res["documents"]
            except Exception:
                # Try other shapes
                ids = res.ids if hasattr(res, "ids") else []
                docs = res.documents if hasattr(res, "documents") else []

        for _id, doc in zip(ids or [], docs or []):
            candidate_ids.append(_id)
            candidate_texts.append(doc)

    if not candidate_texts:
        return ""

    # Rank by simple sequence matcher similarity
    scores = [SequenceMatcher(None, question, t).ratio() for t in candidate_texts]
    ranked = sorted(zip(scores, candidate_texts), key=lambda x: x[0], reverse=True)
    top_texts = [t for _, t in ranked[:n_results]]

    # Return as a single combined string
    return "\n\n".join(top_texts)


def delete_document(doc_id: str):
    """Delete all chunks belonging to `doc_id` from the ChromaDB collection."""
    _ensure_client()

    # Fetch ids for this doc
    try:
        res = _collection.get(where={"doc_id": doc_id})
    except Exception:
        # If get with where is not supported, try query without text
        try:
            res = _collection.query(query_texts=[""], where={"doc_id": doc_id}, n_results=100, include=["ids"])
        except Exception:
            res = {}

    ids = []
    if isinstance(res, dict):
        ids = res.get("ids", [])
    else:
        try:
            ids = res["ids"]
        except Exception:
            ids = res.ids if hasattr(res, "ids") else []

    if not ids:
        return

    try:
        _collection.delete(ids=ids)
    except TypeError:
        # Some chroma versions accept delete(ids=...)
        _collection.delete(ids=ids)
