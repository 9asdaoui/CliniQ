from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from utils.mlflow_evaluation import setup_mlflow
from db.base import Base
from db.session import engine
from routes.rag import router as rag_router
from routes.auth import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import db.models  # noqa: F401
from prometheus_client import Counter, Histogram
import time

origins = [
    "http://localhost:3571",  # dev on host
    "http://localhost:8501",  # Streamlit on host
    "http://frontend:8501",  # Streamlit container
    "http://frontend:5173",  # legacy frontend container
]


@asynccontextmanager
async def lifespan(app: FastAPI):

    # Create database tables
    Base.metadata.create_all(bind=engine)

    setup_mlflow("cliniq-rag-experiment")

    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "http_request_latency_seconds", "Latency of HTTP requests", ["endpoint"]
)

INFERENCE_TIME = Histogram(
    "model_inference_seconds", "Time spent during model inference"
)

ERROR_COUNT = Counter("http_errors_total", "Total number of errors", ["endpoint"])


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    latency = time.time() - start_time

    endpoint = request.url.path
    REQUEST_COUNT.labels(
        method=request.method, endpoint=endpoint, status=response.status_code
    ).inc()

    REQUEST_LATENCY.labels(endpoint=endpoint).observe(latency)

    if response.status_code >= 400:
        ERROR_COUNT.labels(endpoint=endpoint).inc()

    return response


app.include_router(auth_router)
app.include_router(rag_router)


@app.get("/")
def home():
    return {"message": "API is running"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
