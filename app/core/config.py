from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Salon Management API"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: str = "postgresql://salon_user:salon_password@localhost:5432/salon_db"
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Cloudinary Configuration
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""
    CLOUDINARY_URL: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
