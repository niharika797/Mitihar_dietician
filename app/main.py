from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware  # Add this import
from .core.config import settings
from .core.database import connect_to_mongodb, close_mongodb_connection
from .routers import auth, users, diet_plans
from .routers.calculations import router as calculations_router
from .routers.progress import router as progress_router
from .routers.meal_plan import router as meal_plan_router

async def lifespan(app: FastAPI):
    await connect_to_mongodb()
    yield
    await close_mongodb_connection()

# TODO: Switch to RedisStorage before multi-worker/production deployment
# from slowapi.storage import RedisStorage
# limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(diet_plans.router, prefix=f"{settings.API_V1_STR}/diet-plans", tags=["diet-plans"])
app.include_router(calculations_router,prefix=f"{settings.API_V1_STR}/calculations",tags=["calculations"])
app.include_router(progress_router,prefix=f"{settings.API_V1_STR}/progress",tags=["progress"])
app.include_router(meal_plan_router,prefix=f"{settings.API_V1_STR}/meal-plan",tags=["meal-plan"])
@app.get("/")
async def root():
    return {"message": "Welcome to Diet Plan API"}