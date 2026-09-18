from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="GridWise Energy Optimizer API",
    version="2.0.0",
    description="LLM-assisted operator directive interpretation and 24-hour energy optimization.",
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "GridWise API is running"}
