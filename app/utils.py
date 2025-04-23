from enum import Enum

import hashlib
import hmac

from .config import config


def hash_password(input_string: str) -> str:
    """
    Хеширует строку с использованием секретного ключа (HMAC).

    :param input_string: Исходная строка для хеширования
    :param secret_key: Секретный ключ для HMAC
    :return: Хешированная строка
    """
    hmac_object = hmac.new(
        config.SECRET.encode("utf-8"), input_string.encode("utf-8"), hashlib.sha256
    )
    return hmac_object.hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    print(plain_password, hashed_password)
    return hash_password(plain_password) == hashed_password


class StrEnum(str, Enum):
    pass


class RoleEnum(StrEnum):
    admin = "admin"
    teacher = "teacher"