from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy import text
from app.core.database import engine, Base
from app import models  # Ensure models are registered
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Step 4: Verify Database Connection on Startup
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            print("Database connection successful.")
    except Exception as e:
        print(f"Startup failed: Database connection error: {e}")
        # Raising exception here will stop the startup
        raise RuntimeError("Database connection failed") from e
    yield


# Create database tables
Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Zayar Hackathon ISSA", lifespan=lifespan)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def read_root():
    return {"message": "Welcome to Zayar Hackathon ISSA API"}
