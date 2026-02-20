import logging

from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
async def health_check():
    """Health-Check Endpoint für Kubernetes Probes."""
    return {"status": "ok"}

