from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
from app.routes import process, export, feedback

# Load environment variables from .env file
load_dotenv()

# Verify OpenAI API key is loaded (for debugging)
api_key = os.environ.get("OPENAI_API_KEY")
if api_key:
    print(f"✅ OpenAI API key loaded successfully (starts with: {api_key[:12]}...)")
else:
    print("❌ OpenAI API key not found in environment variables")

app = FastAPI(
    title="Lease Logik 2",
    description="AI-native lease abstraction and document intelligence platform",
    version="2.0.0"
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(process.router, prefix="/api", tags=["Process"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])

# Mount storage directories for static file access
os.makedirs("app/storage/exports", exist_ok=True)
app.mount("/exports", StaticFiles(directory="app/storage/exports"), name="exports")

@app.get("/")
async def root():
    return {"message": "Welcome to Lease Logik 2 API"}
