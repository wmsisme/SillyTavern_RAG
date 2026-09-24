import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from backend.schemas.rag import SearchRequest, SearchResponse, AskRequest, AskResponse
from backend.services import rag_service

router = APIRouter()


@router.post("/rag/search", response_model=SearchResponse)
async def rag_search(req: SearchRequest):
    try:
        results = rag_service.search(req.query, top_k=req.top_k)
        return SearchResponse(results=results)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/ask", response_model=AskResponse)
async def rag_ask(req: AskRequest):
    try:
        result = rag_service.ask(req.query)
        return AskResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rag/ask/stream")
async def rag_ask_stream(req: AskRequest):
    def generate():
        try:
            yield json.dumps({"type": "sources", "data": []}, ensure_ascii=False) + "\n"
            for token in rag_service.ask_stream(req.query):
                yield json.dumps({"type": "token", "data": token}, ensure_ascii=False) + "\n"
            yield json.dumps({"type": "done"}, ensure_ascii=False) + "\n"
        except Exception as e:
            yield json.dumps({"type": "error", "data": str(e)}, ensure_ascii=False) + "\n"

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
