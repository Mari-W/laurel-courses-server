from flask import Blueprint, session, render_template, Response, jsonify

from server.env import Env
from server.exercises.course import Course
from server.integration.build_server import build
from server.routing.decorators import authorized_route

cli_bp = Blueprint("cli", __name__)


@cli_bp.route("/version")
@authorized_route
def version():
    return Env.get("CLI_VERSION"), 200


@cli_bp.route("/<course>/cli.py")
@authorized_route
def download(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    user = session.get("user")
    role = course.get_role(user["sub"], is_admin=user["role"] == "admin")
    if role is None or role == "student":
        return "unauthorized", 403

    cli = render_template("cli/cli.py", version=Env.get("CLI_VERSION"), course=str(course),
                          auth_url=Env.get("AUTH_URL"), auth_cookie=Env.get("AUTH_COOKIE"),
                          cli_url=f"{Env.get('PUBLIC_URL')}/cli", git_ssh=Env.get("GITEA_SSH"))
    r = Response(response=cli, status=200, mimetype="text/python")
    r.headers["Content-Type"] = "text/python; charset=utf-8"
    return r


@cli_bp.route("/<course>/logs/<student>/<exercise>")
@authorized_route
def logs(course, student, exercise):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    user = session.get("user")
    role = course.get_role(user["sub"], is_admin=user["role"] == "admin")
    if role is None or role == "student":
        return "unauthorized", 403
    if not course.has_student(student):
        return f"{student} is not enrolled in {course}", 404
    if not course.has_exercise(exercise):
        return f"{course} does not have {exercise}", 404
    b = build.logs(course, student, exercise)
    if not b:
        return "build not found", 404
    return b, 200


@cli_bp.route("/<course>/students")
@authorized_route
def students(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    user = session.get("user")
    role = course.get_role(user["sub"], is_admin=user["role"] == "admin")
    if role is None or role == "student":
        return "unauthorized", 403
    if role == "tutor":
        return jsonify(course.get_tutor_student_names(user["sub"]))
    return jsonify(course.student_names)


@cli_bp.route("/<course>/finished_exercises")
@authorized_route
def finished_exercises(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    user = session.get("user")
    role = course.get_role(user["sub"], is_admin=user["role"] == "admin")
    if role is None or role == "student":
        return "unauthorized", 403

    return jsonify([exercise.name for exercise in course.finished_exercises])
