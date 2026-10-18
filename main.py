import os
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

EMAIL = "24f2005038@ds.study.iitm.ac.in"
ORIGINS = [
    "https://app-bcx7se.example.com",
    "https://exam.sanand.workers.dev",
]

app = FastAPI()
lock = Lock()
buckets = defaultdict(deque)


class RequestContext(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID")

        if not request_id:
            request_id = str(uuid.uuid4())

        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class RateLimiter(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        client = request.headers.get("X-Client-Id", "default")
        now = time.monotonic()

        with lock:
            q = buckets[client]
            while q and now - q[0] >= 10:
                q.popleft()
            if len(q) >= 11:
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=429,
                )
            q.append(now)

        return await call_next(request)


app.add_middleware(RateLimiter)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)
app.add_middleware(RequestContext)


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
