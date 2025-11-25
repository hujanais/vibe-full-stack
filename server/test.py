from core.config import settings

from passlib.context import CryptContext

if __name__ == "__main__":
    # print(settings.DATABASE_URL)
    # print(settings.SECRET_KEY)
    # print(settings.ALGORITHM)
    # print(settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hass7 = pwd_context.hash("test")
    print(hass7)
