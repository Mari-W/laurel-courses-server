import requests
from requests import RequestException

from server.env import Env
from server.error_handling import send_error


class Build:
    @staticmethod
    def build(course: str, student: str, exercise: str):
        r = requests.get(f"{Env.get('BUILD_API_URL')}/build/{course}/{student}{f'/{exercise}' if exercise else ''}",
                         headers={
                             "Authorization": Env.get('BUILD_API_KEY')
                         })
        if r.status_code != 200:
            send_error(Exception("failed to contact build server"))

    @staticmethod
    def logs(course: str, student: str, exercise: str):
        r = requests.get(f"{Env.get('BUILD_API_URL')}/logs/{course}/{student}/{exercise}",
                         headers={
                             "Authorization": Env.get('BUILD_API_KEY')
                         })
        if r.status_code == 404:
            return None
        if r.status_code != 200:
            raise RequestException("failed to get logs from build server")
        return r.text


build = Build()
