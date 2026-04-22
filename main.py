import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="Mock Score API")


@app.get("/", response_class=PlainTextResponse)
def health_check() -> str:
    return "Mock Score API is running"


@app.get("/score")
def get_score() -> dict[str, int]:
    return {"score": 87}


@app.get("/score-unstable")
def get_unstable_score(fail: str | None = Query(default=None)) -> dict[str, int]:
    if fail == "true":
        raise HTTPException(status_code=500, detail="Simulated failure")
    return {"score": 87}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "3000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)