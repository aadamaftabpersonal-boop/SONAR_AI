from fastapi import FastAPI

app = FastAPI(title="Sonar", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness only (FR-27). Readiness with a DB check arrives with the API layer."""
    return {"status": "ok"}
