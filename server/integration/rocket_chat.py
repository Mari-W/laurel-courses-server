import struct
from dataclasses import dataclass

from requests import RequestException
from rocketchat_API.rocketchat import RocketChat

from server.env import Env
from server.exercises.options import CreateCourseOption
from server.integration.auth_server import auth


@dataclass
class Rocket:
    api = RocketChat(Env.get("ROCKET_USER"), Env.get("ROCKET_PASSWORD"), server_url=Env.get("ROCKET_URL"))

    def add_course(self, course: str, options: CreateCourseOption):
        uid = self.get_user_id(options.owner)
        if uid:
            r = self.validate(self.api.teams_create(name=course, team_type=1, room={"readOnly": True},
                                                    members=[uid]))
            self.api.channels_add_owner(room_id=r["team"]["roomId"], user_id=uid)
        else:
            self.validate(self.api.teams_create(name=course, team_type=1, room={"readOnly": True}))
            
        for admin, info in auth.get_admins().items():
            self.add_owner(course, admin, info["name"])

    def remove_course(self, course: str):
        ids = self.get_team_room_ids(course)
        if ids:
            self.validate(self.api.call_api_post("teams.delete", teamName=course, roomsToRemove=ids),
                          ignore_failure=True)
        else:
            self.validate(self.api.call_api_post("teams.delete", teamName=course),
                          ignore_failure=True)

    def add_student(self, course: str, student: str):
        uid = self.get_user_id(student)
        if uid:
            self.validate(self.api.call_api_post("teams.addMembers", teamName=course,
                                                 members=[{"userId": uid, "roles": ["member"]}]))

    def remove_student(self, course: str, student: str):
        uid = self.get_user_id(student)
        if uid:
            self.validate(self.api.call_api_post("teams.removeMember", teamName=course, userId=uid,
                                                 rooms=self.get_team_room_ids(course)), ignore_failure=True)

    def add_tutor(self, course: str, tutor: str, name: str):
        uid = self.get_user_id(tutor)
        if uid:
            self.validate(self.api.call_api_post("teams.addMembers", teamName=course,
                                                 members=[{"userId": uid, "roles": ["moderator"]}]))

            for rid in self.get_team_room_ids(course):
                self.validate(self.api.channels_add_moderator(room_id=rid, user_id=uid), ignore_failure=True)

            # self.validate(self.api.users_update(user_id=uid, name=name))

    def remove_tutor(self, course: str, tutor: str):
        uid = self.get_user_id(tutor)
        if uid:
            self.validate(self.api.call_api_post("teams.removeMember", teamName=course, userId=uid,
                                                 rooms=self.get_team_room_ids(course)), ignore_failure=True)

    def add_owner(self, course: str, owner: str, name: str):
        uid = self.get_user_id(owner)
        if uid:
            self.validate(self.api.call_api_post("teams.addMembers", teamName=course,
                                                 members=[{"userId": uid, "roles": ["owner"]}]))

            for rid in self.get_team_room_ids(course):
                self.validate(self.api.channels_add_owner(room_id=rid, user_id=uid))

            # self.validate(self.api.users_update(user_id=uid, name=name))

    def make_admin(self, admin: str, name: str):
        # uid = self.get_user_id(admin)
        # if uid:
        #   self.validate(self.api.users_update(user_id=uid, name=name, roles=["admin"]))
        pass

    def add_channel(self, course: str, name: str):
        rid = self.validate(self.api.channels_create(name=name))["channel"]["_id"]
        self.validate(self.api.call_api_post("teams.addRooms", teamName=course, rooms=[rid]))
        self.validate(self.api.call_api_post("teams.updateRoom", roomId=rid, isDefault=True))

    def remove_channel(self, course: str, name: str):
        rid = self.get_team_room_id(course, name)
        if rid:
            self.validate(self.api.channels_delete(room_id=rid), ignore_failure=True)

    def add_exercise(self, course: str, exercise: str):
        self.add_channel(course, f"{course}-{exercise}")

    def remove_exercise(self, course: str, exercise: str):
        self.remove_channel(course, f"{course}-{exercise}")

    def delete_user(self, username: str):
        self.validate(self.api.call_api_post("users.delete", username=username), ignore_failure=True)

    @staticmethod
    def validate(response, ignore_failure=False):
        if response.status_code != 200 and not ignore_failure:
            raise RequestException(f"{response.status_code}: {response.text}")
        elif not response.json()["success"] and not ignore_failure:
            raise RequestException(response.text)
        return response.json()

    def get_team_room_ids(self, course: str):
        res = self.validate(self.api.call_api_get("teams.listRooms", teamName=course), ignore_failure=True)
        if res and "rooms" in res:
            return [room["_id"] for room in res["rooms"]]
        return []

    def get_team_room_id(self, course: str, name: str):
        res = self.validate(self.api.call_api_get("teams.listRooms", teamName=course), ignore_failure=True)
        if res and "rooms" in res:
            m = [room["_id"] for room in res["rooms"] if room["name"] == name]
            return m[0] if m else None
        return None

    def get_user_id(self, username: str):
        try:
            r = self.api.users_info(username=username)
            if r.status_code != 200:
                return None
            json = r.json()
            return json["user"]["_id"] if json["success"] else None
        except RequestException as e:
            return None


rocket = Rocket()
