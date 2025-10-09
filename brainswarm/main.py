from fastapi import FastAPI
from brainswarm.api.main import app as brain_app  # Import the existing Brain Swarm API

app = FastAPI(
    title="Brain Swarm Federation",
    description="Multi-Agent Swarm Intelligence System",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/")
def root():
    return {"message": "Brain Swarm Federation is alive!"}

# Mount the existing Brain Swarm API
try:
    app.mount("/api", brain_app)
    print("✅ Brain Swarm API mounted at /api")
except Exception as e:
    print(f"⚠️  Could not mount Brain Swarm API: {e}")
    print("   Make sure the api module is available")

if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Brain Swarm Federation...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔄 ReDoc: http://localhost:8000/redoc")
    print("💚 Health Check: http://localhost:8000/api/health")
    uvicorn.run(app, host="0.0.0.0", port=8000)
