import json
import re

from flask import Blueprint, request

from server.error_handling import send_error
from server.exercises.course import Course
from server.integration.auth_server import auth
from server.integration.build_server import build
from server.integration.gitea_exercises import gitea_exercises
from server.integration.rocket_chat import rocket

hooks_bp = Blueprint("hooks", __name__)


@hooks_bp.route("/gitea-pre-receive", methods=["POST"])
def pre_receive():
    RED = "\033[0;31m"
    RESET = "\033[0m"
    try:
        data = json.loads(request.get_data().decode("utf-8").replace("\n", ","))
    except:
        return f"{RED}PUSH FAILED! Could not load data to identify who's pushing to this repository.{RESET}", 403

    if "user" not in data:
        return f"{RED}PUSH FAILED! Could not identify who's pushing to this repository.{RESET}", 403
    if "repo" not in data or "owner" not in data:
        return f"{RED}PUSH FAILED! Could not who this repository belongs to or what it's name is.{RESET}", 403

    username = data["user"]
    repo = data["repo"]
    owner = data["owner"]
    files = [file for file in data["files"].split(",") if file]

    course = Course.from_str(owner)
    if course is None:
        return "", 200

    # student pushes, check access
    if username == repo:
        pending = [exercise.name for exercise in course.pending_exercises]

        # wildcard
        if "*" in pending:
            return "", 200

        offending = []
        for path in [file.split("/") for file in files]:
            # cannot edit root directory
            if len(path) <= 1:
                offending += ["/".join(path)]
            else:
                file_name = path[-1].strip().lower()
                if file_name == "readme.md" or file_name == ".drone.yml":
                    offending += ["/".join(path)]
                if path[0] not in pending:
                    offending += ["/".join(path)]
        if offending:
            offending_list = "".join("- " + path + "\n" for path in set(offending))
            msg = f"""{RED}PUSH FAILED!

You don't have the permission to modify the following files:
{offending_list}

This error usually occurs if you
    - try to submit an exercise outside its timeframe
    - try to create or change files in directories you're not allowed to
            
You need to make sure that none of the above files are affected by *any* of the commits you're trying to push.{RESET}"""
            return msg, 403

    return "", 200


@hooks_bp.route("/gitea-post-receive", methods=["POST"])
def post_receive():
    try:
        data = json.loads(request.get_data().decode("utf-8").replace("\n", ","))
        print(data)
    except:
        return "", 200

    if "user" not in data:
        return "", 200
    if "repo" not in data or "owner" not in data:
        return "", 200

    username = data["user"]
    repo = data["repo"]
    owner = data["owner"]
    files = [file for file in data["files"].split(",") if file]

    course = Course.from_str(owner)
    if course is None:
        return "", 200

    if not course.has_student(repo):
        return "", 200

    role = course.get_role(username)

    if role is None:
        return "", 200

    paths = [file.split("/") for file in files]

    if role == "student":
        if repo == username:
            edited = [path[0] for path in paths if path]
            for exercise in course.pending_exercises:
                if exercise.name in edited:
                    build.build(str(course), repo, exercise.name)
    else:
        for path in paths:
            if len(path) == 2 and path[-1].strip().lower() == "readme.md":
                exercise = course.get_exercise(path[0])
                if not exercise:
                    continue
                readme = gitea_exercises.get_readme(str(course), exercise.name, repo)
                first_line = readme.split("\n")[0]
                matches = re.findall(r"(\d+[,.]?\d*) */ *(\d+[,.]?\d*)", first_line)
                # no or too many point expressions
                if not matches or len(matches) > 1:
                    return "", 200

                match = matches[0]
                points, _ = float(match[0].replace(",", ".")), float(match[1].replace(",", "."))
                course.set_points(exercise.name, repo, username, points)

    return "", 200


@hooks_bp.route("/rocket-user-created", methods=["POST"])
def user_created():
    username = None
    try:
        data = json.loads(request.get_data().decode("utf-8"))
        username = data["user_name"]

        user = auth.get_user_info(username)
        if not user:
            raise Exception("user not found but joined rocket")

        for course in Course.all_courses():
            role = course.get_role(username, is_admin=user["role"] == "admin")
            if role:
                if role == "student":
                    rocket.add_student(str(course), username)
                elif role == "tutor":
                    rocket.add_tutor(str(course), username, user["name"])
                elif role == "owner" or role == "admin":
                    rocket.add_owner(str(course), username, user["name"])

        if user["role"] == "admin":
            rocket.make_admin(username, user["name"])

    except Exception as e:
        send_error(e)
        if username:
            rocket.delete_user(username)
        return "", 200

    return "", 200
