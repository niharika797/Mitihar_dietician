# from pydantic_settings import BaseSettings

# class Settings(BaseSettings):
#     API_V1_STR: str = "/api"
#     PROJECT_NAME: str = "Diet Plan API"
#     MONGO_URI: str = "mongodb+srv://mitiharadmin3121:johnmarstonM1899@cluster0.dt63p.mongodb.net/mitihar?retryWrites=true&w=majority&appName=Cluster0"
#     DATABASE_NAME: str = "diet_plan"
#     SECRET_KEY: str = "your-secret-key"  # In production, use environment variable
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

# settings= Settings()
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Diet Plan API"
    MONGO_URI: str = "mongodb://localhost:27017"  # Local MongoDB connection
    DATABASE_NAME: str = "diet_plan"
    SECRET_KEY: str = "your-secret-key"  # In production, use environment variable
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

settings = Settings()