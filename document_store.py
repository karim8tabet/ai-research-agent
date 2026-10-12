import io
import os
import uuid
from pypdf import PdfReader
from agent import document_collection

# Every chunk in ChromaDB has an "owner":
#   "shared"      -> documents from the documents/ folder, visible to everyone
#   a session ID  -> a document one visitor uploaded, visible only to them
SHARED_OWNER = "shared"

ALLOWED_EXTENSIONS = (".pdf", ".txt", ".md")
MAX_DOCUMENTS_PER_USER = 5
MAX_CHUNKS_PER_DOCUMENT = 400  # about 200,000 words


def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]


def extract_text(filename, data):
    """Get the plain text out of an uploaded file's bytes."""
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("This PDF is password-protected.")
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    return data.decode("utf-8", errors="replace")


def list_documents(owner_id):
    """The documents a visitor has uploaded, one entry per file."""
    results = document_collection.get(where={"owner": owner_id}, include=["metadatas"])
    documents = {}
    for meta in results["metadatas"]:
        doc_id = meta["doc_id"]
        if doc_id not in documents:
            documents[doc_id] = {"id": doc_id, "filename": meta["source"], "chunks": 0}
        documents[doc_id]["chunks"] += 1
    return list(documents.values())


def shared_document_names():
    """Names of the documents everyone can search."""
    results = document_collection.get(where={"owner": SHARED_OWNER}, include=["metadatas"])
    return sorted({meta["source"] for meta in results["metadatas"]})


def add_document(owner_id, filename, data):
    """Chunk an uploaded file and store it in ChromaDB, tagged with its owner.
    The file itself is never saved to disk; only its text chunks are stored."""
    filename = os.path.basename(filename or "")[:100]
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        raise ValueError("Only PDF, .txt and .md files are supported.")
    if len(list_documents(owner_id)) >= MAX_DOCUMENTS_PER_USER:
        raise ValueError("You can upload up to " + str(MAX_DOCUMENTS_PER_USER) + " documents. Remove one first.")

    try:
        text = extract_text(filename, data)
    except ValueError:
        raise
    except Exception:
        raise ValueError("This file couldn't be read. It may be damaged.")

    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("No text was found in this file. Scanned PDFs (photos of pages) aren't supported.")
    if len(chunks) > MAX_CHUNKS_PER_DOCUMENT:
        raise ValueError("This document is too long. The limit is about 200,000 words.")

    doc_id = uuid.uuid4().hex
    document_collection.add(
        documents=chunks,
        ids=[doc_id + "_chunk_" + str(i) for i in range(len(chunks))],
        metadatas=[{"source": filename, "owner": owner_id, "doc_id": doc_id} for _ in chunks],
    )
    return {"id": doc_id, "filename": filename, "chunks": len(chunks)}


def delete_document(owner_id, doc_id):
    """Delete one document. Matching on owner too means nobody can delete someone else's file."""
    document_collection.delete(where={"$and": [{"owner": owner_id}, {"doc_id": doc_id}]})


def delete_all_documents(owner_id):
    document_collection.delete(where={"owner": owner_id})
