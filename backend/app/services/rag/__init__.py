"""
RAG layer for study notes generation.

Retrieves relevant chunks from uploaded documents before AI generation.

Future extensions (architecture-ready):
- Vector embeddings + semantic search
- Flashcard / MCQ generation from retrieved chunks
- Mind maps and topic summaries
- Chat-with-notes and NotebookLM-style Q&A
- PDF learning assistant with citation tracking
"""

from app.services.rag.retriever import DocumentRetriever

__all__ = ["DocumentRetriever"]
