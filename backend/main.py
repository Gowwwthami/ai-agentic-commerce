from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router


app = FastAPI(
    title="AI Agentic Commerce",
    version="1.0.0",
    description=(
        "AI-powered shopping agent with "
        "recommendations, review intelligence, "
        "and bounded checkout."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router)


@app.get("/")
def root():
    return {
        "message": "AI Agentic Commerce backend is running"
    }