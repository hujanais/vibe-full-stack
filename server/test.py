from core.config import settings

if __name__ == "__main__":
    print(settings.DATABASE_URL)
    print(settings.SECRET_KEY)
    print(settings.ALGORITHM)
    print(settings.ACCESS_TOKEN_EXPIRE_MINUTES)
