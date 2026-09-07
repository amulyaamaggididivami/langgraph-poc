from fastapi import APIRouter

from app.graph.graph import graph
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    result = graph.invoke({"message": req.message, "reply": ""})
    return {"reply": result["reply"]}
