from fastapi import APIRouter, Depends, HTTPException
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..services.user_service import user_service, get_current_user
from ..models.user import User, UserInDB
from ..schemas.user import UserUpdate, UserResponse
from ..core.database import get_database

router = APIRouter()

@router.get("/me", response_model=UserResponse)
async def get_user_profile(current_user: UserInDB = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    update_data: UserUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """Update current user profile"""
    # Remove None values from update data
    data = update_data.model_dump(exclude_unset=True)
    if not data:
        return current_user
        
    success = await user_service.update_user(str(current_user.id), data, db)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update profile")
    
    updated_user = await user_service.get_user_by_id(str(current_user.id), db)
    return updated_user