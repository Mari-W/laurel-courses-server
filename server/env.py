import os

from dotenv import load_dotenv


class Env:

    @staticmethod
    def init():
        load_dotenv()

    @staticmethod
    def get(key: str, default=None, required: bool = True) -> str:
        val = os.getenv(key, default)
        if not val and required:
            raise EnvironmentError(f"could not find required environment variable {key}")
        return val

    @staticmethod
    def get_bool(key: str, required: bool = True) -> bool:
        return Env.get(key, "False", required).lower() in ('true', '1', 't')

    @staticmethod
    def get_int(key: str, required: bool = True):
        try:
            return int(Env.get(key, required=required))
        except ValueError:
            return None
