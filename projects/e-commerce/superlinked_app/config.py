import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ENV_FILENAME = ".env"


class Settings(BaseSettings):
    chunk_size: int = 100
    path_topics: str = (
        "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/topics.json"
    )
    path_product_types: str = (
        "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/product_types.json"
    )
    path_brands: str = (
        "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/brands.json"
    )
    path_dataset: str = (
        "https://storage.googleapis.com/superlinked-recipes/ecommerce-recsys/data/products.json"
    )
    redis_vdb_host: str = "localhost"
    redis_vdb_port: str = "6379"
    model_config = SettingsConfigDict(
        env_file=DEFAULT_ENV_FILENAME, env_file_encoding="utf-8"
    )


def get_env_file_path() -> str:
    dirname = os.path.dirname(__file__)
    rel_path = os.path.join(dirname, DEFAULT_ENV_FILENAME)
    abs_path = os.path.abspath(rel_path)
    return abs_path


settings = Settings(_env_file=get_env_file_path())
