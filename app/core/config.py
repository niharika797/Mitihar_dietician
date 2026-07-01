from pydantic_settings import BaseSettings
from typing import List, Optional, Union
import os
from pydantic import ConfigDict, field_validator
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Diet Plan API"

    # ── JWT / session ─────────────────────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15       # Short-lived — Axios interceptor handles silent refresh
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 10080   # 7 days — lives in HttpOnly cookie only
    RESET_TOKEN_EXPIRE_MINUTES: int = 30        # Password-reset link valid for 30 minutes only

    # ── Cookie security ───────────────────────────────────────────────────
    # Set COOKIE_SECURE=True in production (.env). False only for local HTTP dev.
    COOKIE_SECURE: bool = False

    # ── Password policy ───────────────────────────────────────────────────
    PASSWORD_MIN_LENGTH: int = 8

    # ── CORS ──────────────────────────────────────────────────────────────
    CORS_ORIGINS: Union[str, List[str]] = ["http://localhost:3000"]

    # ── External APIs ─────────────────────────────────────────────────────
    # ── Redis (rate limiter storage) ────────────────────────────────────────
    # Required for any deployment with --workers > 1.
    # Example: redis://localhost:6379
    REDIS_URL: Optional[str] = None

    # ── Trusted proxy CIDR (rate limiter X-Forwarded-For support) ───────────
    # Comma-separated CIDRs whose X-Forwarded-For header is trusted.
    # Dev: 127.0.0.1 (loopback). Production: GCP load balancer IP range.
    # Leave unset to use raw TCP socket IP (safe default, no header trust).
    TRUSTED_PROXY_CIDR: Optional[str] = None

    GEMINI_API_KEY_1: Optional[str] = None
    GEMINI_API_KEY_2: Optional[str] = None
    GEMINI_API_KEY_3: Optional[str] = None
    GEMINI_API_KEY_4: Optional[str] = None
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: Optional[str] = None

    # ── Dev-only flags ────────────────────────────────────────────────────
    # ALLOW_HARD_DELETE=True enables DELETE /admin/patients/{id}/hard-delete
    # which physically removes the patient row (vs the DPDP anonymise).
    # MUST be False in production — set True only in local .env for testing.
    # ── Email verification gate ───────────────────────────────────
    # False = allow login without verified email (current default for dev).
    # Switch to True in production once real email sending is wired up (Phase 7).
    REQUIRE_EMAIL_VERIFICATION: bool = False

    ALLOW_HARD_DELETE: bool = False

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