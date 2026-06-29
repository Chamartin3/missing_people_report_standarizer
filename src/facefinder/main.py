from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from facefinder.api.auth import router as auth_router
from facefinder.api.dashboard import router as dashboard_router
from facefinder.api.faces import router as faces_router
from facefinder.api.identify import router as identify_router
from facefinder.api.images import router as images_router
from facefinder.api.persons import router as persons_router
from facefinder.api.users import router as users_router
from facefinder.data import init_db
from facefinder.services.auth import seed_default_admin


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
    seed_default_admin()
    yield


app = FastAPI(title="FaceFinder", lifespan=lifespan)

# ponytail: wide-open CORS for dev. Lock allow_origins to the real frontend host
# before this goes anywhere public.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(images_router)
app.include_router(faces_router)
app.include_router(persons_router)
app.include_router(identify_router)
app.include_router(users_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
