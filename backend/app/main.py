from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine, test_database_connection
from app.routers import auth_routes, meeting_routes, transcript_routes, summary_routes, export_routes, chatbot_routes, live_routes, websocket_routes
from app.config import settings, validate_required_settings
import logging
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Validate environment variables
try:
    validate_required_settings()
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
    logger.error("Application cannot start without required environment variables")
    raise

# Test database connection
logger.info("Testing database connection...")
if not test_database_connection():
    logger.warning("Database connection test failed, but continuing startup")
    logger.warning("Database tables may not be created automatically")

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified successfully")
except Exception as e:
    logger.warning(f"Could not create tables automatically: {str(e)}")
    logger.info("Tables may already exist or you may need admin privileges")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="AI Meeting Intelligence Platform API",
    version="1.0.0",
    debug=settings.DEBUG,
)

# Add CORS middleware — origin policy lives in app.utils.origins (shared with
# the OAuth redirect validation in auth_routes).
from app.utils.origins import allowed_origins, VERCEL_TEAM_ORIGIN_REGEX

cors_origins = ["*"] if settings.DEBUG else allowed_origins()
if settings.DEBUG:
    logger.info("CORS: DEBUG mode — allowing all origins")
else:
    logger.info(
        f"CORS: Allowing origins: {cors_origins} + regex {VERCEL_TEAM_ORIGIN_REGEX}"
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=VERCEL_TEAM_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include routers - all routes are already prefixed in the router definitions
app.include_router(auth_routes.router)
app.include_router(meeting_routes.router)
app.include_router(transcript_routes.router)
app.include_router(summary_routes.router)
app.include_router(export_routes.router)
app.include_router(chatbot_routes.router)
app.include_router(live_routes.router)
app.include_router(websocket_routes.router)

logger.info("API routers registered successfully")


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(
        f"Response: {request.method} {request.url.path} "
        f"Status: {response.status_code} "
        f"Duration: {process_time:.3f}s"
    )
    
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": settings.APP_NAME,
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
