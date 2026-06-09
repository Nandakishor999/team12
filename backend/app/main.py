"""
main.py — FastAPI application for the TechNovance HR Policy Chatbot.

Startup flow:
  1. CORS middleware is added first (must be outermost).
  2. on_startup event validates that hr_policies.json can be loaded.
  3. /health exposes a compact status payload for uptime monitors.
  4. /api/chat is the single LLM endpoint.
"""

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import google.api_core.exceptions as gapi_exceptions

from app.config import settings
from app.policies import load_policies          # warm up cache on startup
from app.schemas import ChatRequest, ChatResponse
from app.bot import generate_bot_response

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TechNovance HR Chatbot API",
    description=(
        "High-performance FastAPI backend for querying TechNovance HR Policies "
        "powered by Google Gemini 2.0 Flash."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — allow the Next.js dev server and any configured production origins
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Startup event — fail fast if the policy file is missing
# ---------------------------------------------------------------------------
@app.on_event("startup")
async def on_startup() -> None:
    logger.info("Starting TechNovance HR Chatbot API …")
    try:
        load_policies()   # warms the LRU cache — throws if file is missing
        logger.info("HR policy document loaded successfully.")
    except FileNotFoundError as exc:
        logger.critical("CRITICAL: %s — server cannot serve requests.", exc)
        raise  # surface the error so the process exits rather than silently failing


# ---------------------------------------------------------------------------
# Middleware — attach a unique request-id to every request for traceability
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/health", status_code=status.HTTP_200_OK, tags=["Operations"])
async def health_check():
    """
    Lightweight health probe for load balancers and uptime monitors.
    Returns 200 even when the API key is not configured so the container
    stays alive — the /api/chat endpoint will return a 503 in that case.
    """
    return {
        "status": "healthy",
        "company": settings.COMPANY_NAME,
        "api_configured": settings.is_api_configured,
        "version": "1.0.0",
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Send a user message and receive an HR-policy-grounded response.

    - 200  Success
    - 422  Validation error (bad request body)
    - 429  Gemini rate-limit exhausted
    - 503  API key not configured
    - 500  Unexpected internal error
    """
    logger.info(
        "Chat request — message_len=%d  history_len=%d",
        len(request.message),
        len(request.history),
    )

    # Guard: key not configured → return a friendly 503
    if not settings.is_api_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "The AI service is not configured. "
                "Please contact the system administrator to set GEMINI_API_KEY."
            ),
        )

    try:
        bot_reply = generate_bot_response(
            message=request.message,
            history=request.history,
        )
        return ChatResponse(response=bot_reply)

    except RuntimeError as exc:
        # Rate-limit retries exhausted
        logger.warning("Rate-limit error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        )

    except gapi_exceptions.GoogleAPIError as exc:
        logger.error("Gemini API error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error: {exc.message}",
        )

    except Exception as exc:
        logger.exception("Unhandled error in /api/chat")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred. Please try again.",
        )


# ---------------------------------------------------------------------------
# Custom 422 handler — return consistent error JSON shape
# ---------------------------------------------------------------------------
@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "details": str(exc)},
    )


# ---------------------------------------------------------------------------
# Dev entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
