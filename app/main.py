from fastapi import FastAPI
from app.routes import router

app = FastAPI(
    title="GridWise Energy Optimizer API",
    version="1.0.0",
    description="Hackathon API layer for LLM + Optimizer integration"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "GridWise API is running"}
