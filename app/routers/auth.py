from fastapi import APIRouter, HTTPException, Depends, Request
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..services.user_service import UserService
from ..core.security import create_access_token
from ..models.user import User
from datetime import timedelta
from ..core.config import settings
from ..core.database import get_database
from ..core.limiter import limiter
from ..schemas.user import UserCreate, UserResponse
from pymongo.errors import DuplicateKeyError

router = APIRouter()
user_service = UserService()

@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Register a new user"""
    try:
        # Convert UserCreate to User model
        user = User(
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            age=user_data.age,
            gender=user_data.gender,
            height=user_data.height,
            weight=user_data.weight,
            activity_level=user_data.activity_level,
            diet=user_data.diet,
            meal_plan_purchased=False,
            health_condition=user_data.health_condition,
            diabetes_status=user_data.diabetes_status,
            gym_goal=user_data.gym_goal,
            region=user_data.region,
        )
        
        try:
            user_id = await user_service.create_user(user=user, db=db)
        except DuplicateKeyError:
            raise HTTPException(status_code=409, detail="400: Email already registered")
            
        return {
            "message": "User registered successfully",
            "user_id": user_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/token")
@limiter.limit("20/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Login user and return JWT token with rate limiting"""
    user = await user_service.authenticate_user(
        email=form_data.username,
        password=form_data.password,
        db=db
    )
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    refresh_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

from pydantic import BaseModel

class RefreshTokenRequest(BaseModel):
    refresh_token: str

@router.post("/refresh")
async def refresh_token(
    request: Request,
    token_request: RefreshTokenRequest,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Refresh JWT token"""
    try:
        payload = jwt.decode(token_request.refresh_token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    user = await user_service.get_user_by_email(email, db)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }