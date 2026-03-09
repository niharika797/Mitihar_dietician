from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os
from pydantic import ConfigDict, field_validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Diet Plan API"
    
    # Security settings
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15      # Short-lived — Axios interceptor handles silent refresh
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days — lives in HttpOnly cookie only
    
    # CORS settings
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000"]

    # Gemini API (for AI nutrition estimation)
    GEMINI_API_KEY_1: Optional[str] = None

    # Google OAuth (client-side ID token flow)
    # Get these from https://console.cloud.google.com → APIs & Services → Credentials
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None   # kept for future server-side flow
    GOOGLE_REDIRECT_URI: Optional[str] = None    # kept for future server-side flow

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """
        Hard-fail at startup if the SECRET_KEY is the insecure default.
        Every JWT ever issued would be forgeable if this slips into production.
        Generate a safe key with: python -c "import secrets; print(secrets.token_hex(32))"
        """
        if v == "change-me-in-production":
            raise ValueError(
                "SECRET_KEY must be overridden in .env — the default value is not allowed. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        if len(v) < 32:
            raise ValueError(
                "SECRET_KEY must be at least 32 characters long for HS256 security."
            )
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return v # Pydantic will handle it if it's already a list or other valid type

    model_config = ConfigDict(
        case_sensitive=True, 
        env_file=".env", 
        extra="ignore"
    )

settings = Settings()