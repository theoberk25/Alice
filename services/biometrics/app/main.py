import secrets
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
import numpy as np
from .config import Settings
from .schemas import Identity, Capture, Enrollment, VerificationResult
from .engine import ArcFaceEngine, IdentityEngine, unit, similarity
from .imaging import CaptureError
from .storage import EnrollmentStore

def create_app(settings: Settings | None = None, engine: IdentityEngine | None = None):
    config = settings or Settings.from_env()
    mutex = threading.Lock()

    @asynccontextmanager
    async def lifespan(app):
        app.state.engine = engine or ArcFaceEngine(config)
        app.state.store = EnrollmentStore(config.data_dir)
        yield

    api = FastAPI(title="ALICE Face Identity", version="0.1.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

    def authorized(authorization: str = Header(default="")):
        if len(config.token) < 32:
            raise HTTPException(503, "SERVICE_TOKEN_NOT_CONFIGURED")
        if not secrets.compare_digest(authorization, f"Bearer {config.token}"):
            raise HTTPException(401, "UNAUTHORIZED_LOCAL_CLIENT")

    @api.middleware("http")
    async def bound_body(request: Request, call_next):
        # Bound both advertised and streamed body size before JSON/base64 decoding.
        length = request.headers.get("content-length", "0")
        if not length.isdigit() or int(length) > 22_000_000:
            return JSONResponse({"detail": "REQUEST_TOO_LARGE"}, status_code=413)
        total = 0
        chunks = []
        async for chunk in request.stream():
            total += len(chunk)
            if total > 22_000_000:
                return JSONResponse({"detail": "REQUEST_TOO_LARGE"}, status_code=413)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        return await call_next(request)

    def ready():
        if not api.state.engine.ready:
            raise HTTPException(503, api.state.engine.error)

    @api.get("/health", dependencies=[Depends(authorized)])
    def health():
        return {"status": "READY" if api.state.engine.ready else "UNAVAILABLE", "identity": "ArcFace", "liveness": "NOT_CONFIGURED", "detail": api.state.engine.error}

    @api.get("/model-info", dependencies=[Depends(authorized)])
    def model_info():
        return {"model": config.model_name, "provider": "arcface", "threshold": config.threshold, "ready": api.state.engine.ready, "liveness": "NOT_CONFIGURED"}

    @api.post("/enroll", dependencies=[Depends(authorized)])
    def enroll(request: Enrollment):
        ready()
        if len(set(request.frames)) < 5:
            raise HTTPException(422, "CAPTURE_FIVE_DISTINCT_FRAMES")
        try:
            with mutex:
                vectors = [api.state.engine.embedding(frame) for frame in request.frames]
                reference = unit(np.mean(vectors, axis=0))
                if any(similarity(vector, reference) < max(config.threshold, 0.5) for vector in vectors):
                    raise CaptureError("INCONSISTENT_ENROLLMENT_IDENTITY")
                api.state.store.put(request.technician_id, reference, config.model_name, len(vectors))
            return {"status": "ENROLLED", "technician_id": request.technician_id, "usable_samples": len(vectors), "provider": "arcface", "liveness": "NOT_CONFIGURED"}
        except (CaptureError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @api.post("/verify", response_model=VerificationResult, dependencies=[Depends(authorized)])
    def verify(request: Capture):
        ready()
        try:
            with mutex:
                reference = api.state.store.get(request.technician_id, config.model_name)
                scores = [similarity(api.state.engine.embedding(frame), reference) for frame in request.frames]
            # Every supplied frame must match the one claimed identity.
            score = min(scores)
            return VerificationResult(result="PASS" if score >= config.threshold else "FAIL", similarity=round(score, 4), threshold=config.threshold)
        except (CaptureError, ValueError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @api.post("/remove", dependencies=[Depends(authorized)])
    def remove(request: Identity):
        with mutex:
            api.state.store.remove(request.technician_id)
        return {"status": "REMOVED", "technician_id": request.technician_id}

    return api

app = create_app()
