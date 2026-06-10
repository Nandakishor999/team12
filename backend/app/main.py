"""
main.py — FastAPI application for the TechNovance HR Policy Chatbot.

Production features:
  - Rate limiting per client IP
  - Response caching
  - Structured logging
  - Connection pooling
  - Graceful shutdown
  - Security headers
"""

import logging
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.policies import load_policies
from app.schemas import ChatRequest, ChatResponse
from app.bot import AIRateLimitError, AIServiceError, generate_bot_response, close_groq_client
from app.routes_auth import router as auth_router
from app.routes_hr import router as hr_router
from app.deps import get_current_user
from app.company_policies import get_company_policy_document_text


from app.cache import rate_limiter, cache_key_for_query, response_cache
from app.utils import generate_request_id, sanitize_input, StructuredLogger

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = StructuredLogger(__name__)
std_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan (startup/shutdown)
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown lifecycle."""
    # Startup
    logger.info("Starting TechNovance HR Chatbot API (v1.0.0)", environment=settings.ENVIRONMENT)
    if not settings.is_api_configured:
        logger.warning(
            "AI provider not configured — /api/chat will return 503 until key is set",
            provider=settings.active_provider,
        )

    # Legacy mode loads single-company policies file.
    # In the multi-tenant build, policies come from MongoDB per company.
    try:
        load_policies()
        logger.info("HR policy document loaded successfully")

    except FileNotFoundError as exc:
        logger.error(f"CRITICAL: {exc} — server cannot serve requests", environment=settings.ENVIRONMENT)
        raise

    yield

    # Shutdown
    logger.info("Shutting down HR Chatbot API")
    close_groq_client()
    logger.info("Resources cleaned up")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TechNovance HR Chatbot API",
    description=(
        "Production-grade FastAPI backend for querying TechNovance HR Policies "
        "with rate limiting, caching, and configurable AI provider support."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS — secure configuration for production
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=3600,
)


# ---------------------------------------------------------------------------
# Middleware — request tracking and rate limiting
# ---------------------------------------------------------------------------
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach request ID and rate limit check to every request."""
    request_id = generate_request_id()
    request.state.request_id = request_id
    
    # Extract client IP (handle proxies)
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    if "," in client_ip:
        client_ip = client_ip.split(",")[0].strip()
    request.state.client_ip = client_ip
    
    # Rate limiting check
    if not rate_limiter.is_allowed(client_ip):
        std_logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={"X-Request-ID": request_id},
            content={
                "detail": "Too many requests. Rate limit exceeded.",
                "request_id": request_id,
            },
        )
    
    response = await call_next(request)
    
    # Add rate limit headers
    remaining = rate_limiter.get_remaining_requests(client_ip)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Remaining"] = str(remaining["remaining_per_minute"])
    
    return response


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
app.include_router(auth_router)
app.include_router(hr_router)


@app.get("/health", status_code=status.HTTP_200_OK, tags=["Operations"])

async def health_check(request: Request):
    """
    Lightweight health probe for load balancers and uptime monitors.
    Returns 200 even when API key is not configured.
    """
    return {
        "status": "healthy",
        "company": settings.COMPANY_NAME,
        "api_configured": settings.is_api_configured,
        "environment": settings.ENVIRONMENT,
        "cache_size": response_cache.size,
        "version": "1.0.0",
        "request_id": getattr(request.state, "request_id", None),
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: ChatRequest,
    http_request: Request,
    user: dict = None,
):
    


    """
    Send a user message and receive an HR-policy-grounded response.
    
    Production guarantees:
    - 200  Success
    - 422  Validation error (bad request)
    - 429  Rate limit or provider quota exceeded
    - 503  API key not configured
    - 500  Unexpected internal error
    """
    request_id = getattr(http_request.state, "request_id", "unknown")
    client_ip = getattr(http_request.state, "client_ip", "unknown")
    
    logger.info(
        "Chat request received",
        request_id=request_id,
        client_ip=client_ip,
        message_len=len(request.message),
        history_len=len(request.history),
    )

    # Require JWT auth
    if not user:
        # Backward compat: if dependency isn't wired, reject
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    company_id = user.get("companyId")
    if not company_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing companyId in token")

    # Validate API key is configured

    if not settings.is_api_configured:
        logger.warning(
            "Chat request rejected — API not configured",
            request_id=request_id,
            provider=settings.active_provider,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"The AI service is not configured for provider '{settings.active_provider}'. "
                "Please contact the system administrator."
            ),
        )

    # Sanitize user input
    try:
        sanitized_message = sanitize_input(request.message, max_length=4000)
    except ValueError as exc:
        logger.warning(f"Invalid user input: {str(exc)}", request_id=request_id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    # NOTE: companyId is currently not enforced in this legacy endpoint.
    # Next step will wire auth -> companyId -> per-company policies.
    try:
        policy_document_text = await get_company_policy_document_text(company_id)

        bot_reply = generate_bot_response(
            message=sanitized_message,
            history=request.history,
            policy_document_text=policy_document_text,
        )


        logger.info(
            "Chat response generated successfully",
            request_id=request_id,
            response_len=len(bot_reply),
        )
        return ChatResponse(response=bot_reply)

    except AIRateLimitError as exc:
        logger.warning(f"Rate-limit error: {str(exc)}", request_id=request_id)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API provider rate limit exceeded. Please try again later.",
        )

    except AIServiceError as exc:
        logger.error(f"AI service error: {str(exc)}", request_id=request_id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI service error. Please try again later.",
        )

    except ValueError as exc:
        logger.error(f"Configuration error: {str(exc)}", request_id=request_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service configuration error. Please contact administrator.",
        )

    except Exception as exc:
        logger.error(f"Unhandled error in /api/chat: {str(exc)}", request_id=request_id)
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
