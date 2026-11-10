"""Ruta del chat con la IA."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai.gemini import AIError
from ai.orchestrator import generate_reply
from services.validation import CHAT_MAX_MESSAGES, CHAT_MESSAGE_MAX_LENGTH

router = APIRouter(tags=["Chat con IA"])


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(..., max_length=CHAT_MESSAGE_MAX_LENGTH)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, max_length=CHAT_MAX_MESSAGES)


@router.post("/chat", summary="Responde la conversación usando la IA y el motor de búsqueda")
def chat(request: ChatRequest):
    try:
        return generate_reply([message.model_dump() for message in request.messages])
    except AIError as error:
        print("Error de la IA:", error)
        raise HTTPException(
            status_code=502,
            detail="El asistente no está disponible en este momento. Intenta de nuevo en unos segundos.",
        )
