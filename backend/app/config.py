from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "E-Commerce Recommendation Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # MongoDB
    MONGODB_URL: str = "mongodb://localhost:27017"
    MONGODB_DB: str = "recommendation_engine"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_CACHE_TTL: int = 300  # 5 minutes

    # Model
    MODEL_PATH: str = "training/models/recommender_model.pkl"
    TOP_N_RECOMMENDATIONS: int = 10

    # A/B Testing
    AB_TEST_SPLIT: float = 0.5  # 50% to model_b

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
