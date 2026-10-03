import os
from typing import List
from dotenv import load_dotenv

load_dotenv()



class Settings:
    # Application Metadata
    APP_NAME: str = os.getenv("APP_NAME", "VETRA")
    APP_ENV: str = os.getenv("APP_ENV", "development").lower()
    DEBUG: bool = os.getenv("DEBUG", "true" if APP_ENV == "development" else "false").lower() in ("true", "1", "yes")

    # Network & Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # CORS & Security
    ALLOWED_ORIGINS_RAW: str = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:8501,http://127.0.0.1:8501,http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
    )
    ALLOWED_HOSTS_RAW: str = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        if not self.ALLOWED_ORIGINS_RAW:
            return ["http://localhost:8501", "http://127.0.0.1:8501"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS_RAW.split(",") if origin.strip()]

    @property
    def ALLOWED_HOSTS(self) -> List[str]:
        if not self.ALLOWED_HOSTS_RAW:
            return ["*"]
        return [host.strip() for host in self.ALLOWED_HOSTS_RAW.split(",") if host.strip()]

    # MongoDB Atlas
    MONGODB_URL: str = os.getenv("MONGODB_URL", "")
    MONGODB_DATABASE: str = os.getenv("MONGODB_DATABASE", "vetra")
    MONGODB_MAX_POOL_SIZE: int = int(os.getenv("MONGODB_MAX_POOL_SIZE", "50"))
    MONGODB_MIN_POOL_SIZE: int = int(os.getenv("MONGODB_MIN_POOL_SIZE", "5"))
    MONGODB_CONNECT_TIMEOUT_MS: int = int(os.getenv("MONGODB_CONNECT_TIMEOUT_MS", "5000"))
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = int(os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "5000"))

    # AI & External APIs
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # JWT Authentication
    JWT_SECRET: str = os.getenv("JWT_SECRET", "development-secret")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # Security & Middlewares
    SECURITY_HEADERS_ENABLED: bool = os.getenv("SECURITY_HEADERS_ENABLED", "true").lower() in ("true", "1", "yes")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "25"))
    RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
    RATE_LIMIT_REQUESTS: int = int(os.getenv("RATE_LIMIT_REQUESTS", "120"))
    RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
    WEBSOCKET_AUTH_REQUIRED: bool = os.getenv("WEBSOCKET_AUTH_REQUIRED", "false").lower() in ("true", "1", "yes")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO" if APP_ENV == "production" else "DEBUG").upper()

    def validate_production_settings(self) -> List[str]:
        """
        Validate critical security parameters for production deployments.
        Returns a list of validation error descriptions (without revealing secrets).
        """
        errors = []

        if self.APP_ENV == "production":
            # 1. JWT Secret strength and placeholder rejection
            insecure_secrets = [
                "development-secret", "secret", "change-me", "default",
                "123456", "password", "jwt-secret", "admin"
            ]
            if not self.JWT_SECRET or self.JWT_SECRET.lower() in insecure_secrets or len(self.JWT_SECRET) < 32:
                errors.append("Production requires a high-entropy JWT_SECRET of at least 32 characters.")

            # 2. MongoDB URL presence
            if not self.MONGODB_URL:
                errors.append("Production requires MONGODB_URL to be set.")

            # 3. Debug mode must be disabled in production
            if self.DEBUG:
                errors.append("DEBUG mode must be disabled in production.")

            # 4. Wildcard CORS rejection in production
            if "*" in self.ALLOWED_ORIGINS:
                errors.append("Wildcard '*' CORS origins are strictly disallowed in production.")

            # 5. Rate limiting must be enabled in production
            if not self.RATE_LIMIT_ENABLED:
                errors.append("RATE_LIMIT_ENABLED must be true in production.")

        return errors


settings = Settings()