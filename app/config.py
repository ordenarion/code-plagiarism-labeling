from pydantic_settings import BaseSettings


class Config(BaseSettings):
    DB_URI: str
    SECRET: str
    ADMIN_LOGIN: str
    ADMIN_PASSWORD: str

    class Config:
        str_strip_whitespace = True
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


config = Config()
