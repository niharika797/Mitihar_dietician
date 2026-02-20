from datetime import datetime
from typing import Optional
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from motor.motor_asyncio import AsyncIOMotorDatabase
from ..core.config import settings
from ..core.security import verify_password, get_password_hash
from ..core.exceptions import UserNotFoundException, EmailAlreadyExistsException, InvalidCredentialsException
from ..models.user import User, UserInDB
from ..core.database import get_database
from bson import ObjectId

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

class UserService:
    def __init__(self):
        self.collection_name = "users"

    def get_collection(self, db: AsyncIOMotorDatabase):
        """Get the users collection."""
        return db[self.collection_name]

    async def create_user(self, user: User, db: AsyncIOMotorDatabase) -> str:
        """Create a new user."""
        collection = self.get_collection(db)
        
        # Check if email already exists
        if await collection.find_one({"email": user.email}):
            raise EmailAlreadyExistsException()

        user_dict = user.dict()
        user_dict["hashed_password"] = get_password_hash(user_dict.pop("password"))
        user_dict["created_at"] = datetime.utcnow()
        user_dict["updated_at"] = datetime.utcnow()

        result = await collection.insert_one(user_dict)
        return str(result.inserted_id)

    async def get_user_by_email(self, email: str, db: AsyncIOMotorDatabase) -> Optional[UserInDB]:
        """Retrieve user by email."""
        collection = self.get_collection(db)
        user_dict = await collection.find_one({"email": email})
        
        if user_dict:
            # Convert ObjectId to string for the id field
            user_dict["id"] = str(user_dict.pop("_id"))
            return UserInDB(**user_dict)
        return None

    async def get_user_by_id(self, user_id: str, db: AsyncIOMotorDatabase) -> Optional[UserInDB]:
        """Retrieve user by ID."""
        collection = self.get_collection(db)
        try:
            user_dict = await collection.find_one({"_id": ObjectId(user_id)})
            if user_dict:
                # Convert ObjectId to string for the id field
                user_dict["id"] = str(user_dict.pop("_id"))
                return UserInDB(**user_dict)
        except:
            return None
        return None

    async def authenticate_user(self, email: str, password: str, db: AsyncIOMotorDatabase) -> Optional[UserInDB]:
        """Authenticate user with email and password."""
        user = await self.get_user_by_email(email, db)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    async def update_user(self, user_id: str, update_data: dict, db: AsyncIOMotorDatabase) -> bool:
        """Update user information."""
        collection = self.get_collection(db)
        update_data["updated_at"] = datetime.utcnow()
        
        try:
            result = await collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            return result.modified_count > 0
        except:
            return False

# Update the get_current_user function
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncIOMotorDatabase = Depends(get_database)
) -> UserInDB:
    """Get current user from JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise InvalidCredentialsException()
    except JWTError:
        raise InvalidCredentialsException()

    user_service = UserService()
    user = await user_service.get_user_by_email(email, db)
    if user is None:
        raise UserNotFoundException()
    return user