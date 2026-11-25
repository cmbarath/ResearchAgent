import asyncio
import json
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import ollama

from agent import CustomReActAgent
from config import settings
from models import AgentEvent, ResearchRequest

app = FastAPI(
    title="Research Agent API",
    description="Custom ReAct Loop Research Agent powered by local Ollama llama3.2:latest",
    version="1.0.0",
)

# Enable CORS for frontend Vite dev server (and any local port)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint that verifies Ollama connection and model availability."""
    ollama_ok = False
    model_found = False
    error_msg = None

    try:
        client = ollama.Client(host=settings.OLLAMA_HOST)
        models_resp = client.list()
        ollama_ok = True
        model_names = [m.model for m in models_resp.models]
        model_found = settings.OLLAMA_MODEL in model_names or any(
            m.startswith(settings.OLLAMA_MODEL.split(":")[0]) for m in model_names
        )
    except Exception as e:
        error_msg = str(e)

    return {
        "status": "ok" if (ollama_ok and model_found) else "degraded",
        "ollama_host": settings.OLLAMA_HOST,
        "ollama_model": settings.OLLAMA_MODEL,
        "ollama_connected": ollama_ok,
        "model_available": model_found,
        "error": error_msg,
    }


async def sse_event_stream(question: str) -> AsyncGenerator[str, None]:
    """Generates Server-Sent Events (SSE) from the ReAct agent loop."""
    agent = CustomReActAgent()
    try:
        async for event in agent.run(question=question):
            # Format as valid SSE message: "data: <json>\n\n"
            json_data = event.model_dump_json()
            yield f"data: {json_data}\n\n"
            # Small yield to ensure event loop flushes to socket
            await asyncio.sleep(0.01)
    except asyncio.CancelledError:
        # Client disconnected
        pass
    except Exception as exc:
        err_event = AgentEvent(
            type="error",
            step=0,
            error=f"Agent stream error: {str(exc)}",
            message="Server encountered an unexpected error during research.",
        )
        yield f"data: {err_event.model_dump_json()}\n\n"


@app.post("/api/research")
async def start_research(request: ResearchRequest):
    """Initiates a research session with the custom ReAct agent and streams progress via SSE."""
    clean_question = request.question.strip()
    if not clean_question:
        raise HTTPException(status_code=400, detail="Research question cannot be empty.")

    return StreamingResponse(
        sse_event_stream(clean_question),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
