from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.app.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "WrongBook API is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}
