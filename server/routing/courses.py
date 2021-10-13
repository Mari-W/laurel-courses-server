from datetime import datetime

from flask import Blueprint, redirect, jsonify, session, make_response
from server.env import Env
from server.exercises.course import Course
from server.integration.gitea_exercises import gitea_exercises
from server.routing.auth import cors
from server.routing.decorators import authorized_route

courses_bp = Blueprint("courses", __name__)


@courses_bp.route("/list", methods=["GET"])
@authorized_route
def list_courses():
    # note that here role can be null if user is not enrolled
    # dict: { "course_name": { "role": "Students/Tutors/Owners"/null, "joinable": True/False }, "course_name2": { .. } }
    user = session.get("user")
    username = user["sub"]
    role = user["role"]
    # also check if user is admin here because on login the user doesnt exist and this page loads after login in gitea
    if role == "admin":
        gitea_exercises.make_admin(user)
        # drone.make_admin(username)

    return cors(jsonify({
        str(course): {
            "role": course.get_role(username, is_admin=role == "admin"),
            "open": course.is_open,
            "restricted": course.is_restricted,
            "display_name": course.entity.display_name,
            "website": course.entity.website,
        }
        for course in Course.all_courses()
    }))


@courses_bp.route("/<course>/<student>/tutor", methods=["GET"])
@authorized_route
def tutor(course, student):
    user = session.get("user")
    username = user["sub"]
    course = Course.from_str(course)
    if not course:
        return cors(make_response(("course not found", 500)))

    if course.get_role(username, is_admin=user["role"] == "admin") is None:
        return cors(make_response(("unauthorized", 401)))

    if not course.has_student(student):
        return cors(make_response(("not a student", 404)))
    tutor = course.get_student_tutor(student)
    if not tutor:
        return cors(make_response(("tutor not found", 404)))

    return cors(jsonify(tutor.to_dict()))


@courses_bp.route("/<course>/<student>/exercises", methods=["GET"])
@authorized_route
def exercises(course, student):
    user = session.get("user")
    username = user["sub"]
    course = Course.from_str(course)
    if not course:
        return cors(make_response(("course not found", 500)))

    if course.get_role(username, is_admin=user["role"] == "admin") is None:
        return cors(make_response(("unauthorized", 401)))

    if not course.has_student(student):
        return cors(make_response(("not a student", 404)))

    now = datetime.now()

    def _msg(exercise):
        if exercise.start < now < exercise.end:
            left = exercise.end - now
            hours, remainder = divmod(left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            r = ""
            if left.days > 0:
                r += f"{left.days}d "
            if hours > 0:
                r += f"{str(hours)}h "
            if minutes > 0:
                r += f"{str(minutes)}m "
            if left.days == hours == minutes == 0:
                r += f"{str(seconds)}s "
            return r + "left"
        elif exercise.start > now:
            return f"{exercise.start.strftime('%d.%m at %H:%M')} to {exercise.start.strftime('%d.%m at %H:%M')}"

    (exercises, student_stats) = course.get_student_exercises_stats(student, return_exercises=True)
    return cors(jsonify({
        "percentage": student_stats["percentage"],
        "total": student_stats["total"],
        "max_total": student_stats["max_total"],
        "exercises": {
            exercise.name: {
                "finished": exercise.end < now,
                "important_message": exercise.start < now < exercise.end,
                "message": _msg(exercise),
                "points": student_stats["exercises"][exercise.name]["points"]
                if exercise.name in student_stats["exercises"] else None,
                "max_points": exercise.points
            } for exercise in exercises
        }}))


@courses_bp.route("/join", methods=["POST"])
@authorized_route
def join():
    course = Course.from_req()
    if not course:
        return "course not found", 500

    if not course.is_open:
        return "course is currently not open for registration", 500

    student = session.get("user")["sub"]
    err = course.add_student(student)
    if err:
        return err + '. please contact server administrator. meanwhile you can ' \
                     f'<a href="{Env.get("GITEA_URL")}">return to git</a>', 500

    return cors(redirect(f"{Env.get('GITEA_URL')}/{str(course)}/{student}"))
