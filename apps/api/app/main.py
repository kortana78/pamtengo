from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.routes import router as v1_router
from app.core.config import settings
from app.core.logging import log
from app.core.rate_limit import RateLimitMiddleware
from app.db.session import SessionLocal, init_db
from app.models.entities import User


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        db = SessionLocal()
        try:
            if not db.query(User).filter(User.email == settings.seed_admin_email).first():
                db.add(User(email=settings.seed_admin_email, role=settings.seed_admin_role))
                db.commit()
                log.info("Seeded dev admin user")
        finally:
            db.close()
        yield

    app = FastAPI(
        title="Pamtengo API",
        version="0.1.0",
        description="AI sales intelligence platform API (mock email, bounded agent).",
        lifespan=lifespan,
    )

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RateLimitMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422, content={"detail": "Validation failed", "errors": exc.errors()}
        )

    @app.get("/health")
    def health():
        return {"status": "ok", "service": "pamtengo-api", "ai": settings.ai_provider}

    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
