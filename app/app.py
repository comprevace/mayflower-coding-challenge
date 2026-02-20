import uvicorn

from src.endpoint import app  # noqa: F401

if __name__ == "__main__":
    uvicorn.run("src.endpoint:app", host="0.0.0.0", port=8000, reload=True)
