from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..services.user_service import UserService
from ..core.security import create_access_token
from ..models.user import User
from datetime import timedelta
from ..core.config import settings
from ..core.database import get_database
from ..schemas.user import UserCreate, UserResponse  # Add these imports

router = APIRouter()
user_service = UserService()

@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,  # Changed from User to UserCreate
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
        )
        
        user_id = await user_service.create_user(user=user, db=db)
        return {
            "message": "User registered successfully",
            "user_id": user_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Login user and return JWT token"""
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
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }