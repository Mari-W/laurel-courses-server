import requests
from requests import RequestException

from server.env import Env


class Auth:
    @staticmethod
    def get_user_info(user: str):
        try:
            r = requests.get(f"{Env.get('AUTH_LOCAL_URL')}/api/user/{user}", headers={
                "Authorization": Env.get('AUTH_API_KEY')
            })
            if r.status_code != 200:
                return None
            return r.json()
        except RequestException:
            return None

    @staticmethod
    def get_users():
        try:
            r = requests.get(f"{Env.get('AUTH_LOCAL_URL')}/api/users", headers={
                "Authorization": Env.get('AUTH_API_KEY')
            })
            if r.status_code == 404:
                return None
            return r.json()
        except RequestException:
            return None

    @staticmethod
    def get_admins():
        try:
            r = requests.get(f"{Env.get('AUTH_LOCAL_URL')}/api/admins", headers={
                "Authorization": Env.get('AUTH_API_KEY')
            })
            if r.status_code == 404:
                return None
            return r.json()
        except RequestException:
            return None

    def is_admin(self, user: str):
        user = self.get_user_info(user)
        return user is not None and user == "admin"


auth = Auth()
