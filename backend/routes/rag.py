"""RAG knowledge base REST API."""

from fastapi import APIRouter, Query

from backend.services.rag_service import get_rag_service

router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    top_k: int = Query(3, ge=1, le=10),
    category: str | None = Query(None),
):
    """Search the advertising knowledge base."""
    rag = get_rag_service()
    results = rag.search(q, top_k=top_k, category=category)
    return {"query": q, "results": results, "total": len(results)}


@router.get("/categories")
async def list_categories():
    """List all knowledge categories."""
    rag = get_rag_service()
    return {"categories": rag.get_categories()}


@router.get("/stats")
async def rag_stats():
    """Get knowledge base statistics."""
    rag = get_rag_service()
    return rag.get_stats()
