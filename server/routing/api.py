from io import BytesIO

from flask import Blueprint, jsonify, request, Response

from server.exercises.course import Course
from server.integration.auth_server import auth
import matplotlib.pyplot as mpl

from server.routing.decorators import admin_route

api_bp = Blueprint("api", __name__)


@api_bp.route("/courses", methods=["GET"])
@admin_route
def courses():
    return jsonify(Course.all_courses())


@api_bp.route("/course/<course>/tutors", methods=["GET"])
@admin_route
def tutors(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return jsonify([{**info, "students": course.get_tutor_student_names(info["username"])} for info in course.tutors])


@api_bp.route("/course/<course>/is_tutor/<tutor>", methods=["GET"])
@admin_route
def is_tutor(course, tutor):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if not course.has_tutor(tutor):
        return "not a tutor", 404
    return "", 200


@api_bp.route("/course/<course>/exercise/<exercise>/graph", methods=["GET"])
@admin_route
def graphs(course, exercise):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404
    exercise = course.get_exercise(exercise)
    if not exercise:
        return "exercise not found", 404

    mpl.plot(
        list(range(round(exercise.points) + 1)),
        [course.get_students_with_points(points, exercise.name) for points in range(round(exercise.points) + 1)],
    )
    mpl.xlabel("Points")
    mpl.ylabel("Students")
    mpl.title("Points per Student")
    mpl.gcf().gca().yaxis.get_major_locator().set_params(integer=True)
    mpl.gcf().gca().xaxis.get_major_locator().set_params(integer=True)

    buf = BytesIO()
    mpl.savefig(buf, format="png")
    return Response(buf.getvalue(), mimetype='image/png')


@api_bp.route("/course/<course>/exercises/stats", methods=["GET"])
@admin_route
def stats(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    res = dict()
    include_ungraded = "include_ungraded" in request.args

    exercises = course.exercises
    users = auth.get_users()

    for student in course.students:
        res[student.username] = {
            "matrikelnummer": users[student.username]["matrikelnummer"] if student.username in users else None,
            **course.get_student_exercises_stats(student.username, exercises=exercises,
                                                 include_ungraded=include_ungraded)
        }
    return jsonify(res)