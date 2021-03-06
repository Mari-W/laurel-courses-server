# from io import BytesIO

from flask import Blueprint, jsonify, request

from server.exercises.course import Course
from server.integration.auth_server import auth
# import matplotlib.pyplot as mpl

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


# @api_bp.route("/course/<course>/exercise/<exercise>/points/graph", methods=["GET"])
# @admin_route
# def points(course, exercise):
#     course = Course.from_str(course)
#     if not course:
#         return "course not found", 404
#     exercise = course.get_exercise(exercise)
#     if not exercise:
#         return "exercise not found", 404
#
#     mpl.plot(
#         list(range(round(exercise.points) + 1)),
#         [course.get_students_with_points(points, exercise.name) for points in range(round(exercise.points) + 1)],
#     )
#     mpl.xlabel("Points")
#     mpl.ylabel("Students")
#     mpl.title(f"Points per Students in {exercise.name}")
#     mpl.gcf().gca().yaxis.get_major_locator().set_params(integer=True)
#     mpl.gcf().gca().xaxis.get_major_locator().set_params(integer=True)
#
#     buf = BytesIO()
#     mpl.savefig(buf, format="png")
#     return Response(buf.getvalue(), mimetype='image/png')
#
#
# @api_bp.route("/course/<course>/exercise/<exercise>/time/graph", methods=["GET"])
# @admin_route
# def time(course, exercise):
#     course = Course.from_str(course)
#     if not course:
#         return "course not found", 404
#     exercise = course.get_exercise(exercise)
#     if not exercise:
#         return "exercise not found", 404
#
#     time_spent = course.get_time_spent(exercise.name)
#     max_spent = max(time_spent.keys()) if len(time_spent.keys()) > 0 else 0
#
#     mpl.plot(
#         list(range(max_spent + 1)),
#         [time_spent[spent] if spent in time_spent else 0 for spent in list(range(max_spent + 1))],
#     )
#     mpl.xlabel("Time Spent (in hours, rounded)")
#     mpl.ylabel("Students")
#     mpl.title("Time Spent per Students")
#     mpl.gcf().gca().yaxis.get_major_locator().set_params(integer=True)
#     mpl.gcf().gca().xaxis.get_major_locator().set_params(integer=True)
#
#     buf = BytesIO()
#     mpl.savefig(buf, format="png")
#     return Response(buf.getvalue(), mimetype='image/png')

@api_bp.route("/course/<course>/exercises", methods=["GET"])
@admin_route
def exercises(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return jsonify([{"name": exercise.name, "points": exercise.points, "start": exercise.start.isoformat(),
                     "end": exercise.end.isoformat()} for exercise in course.finished_exercises])


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


@api_bp.route("/course/<course>/exercise/<exercise>/stats", methods=["GET"])
@admin_route
def exercise_stats(course, exercise):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404
    exercise = course.get_exercise(exercise)
    if not exercise:
        return "exercise not found", 404

    include_ungraded = "include_ungraded" in request.args
    include_time_spent = "include_time_spent" in request.args

    return jsonify(course.get_exercise_stats(exercise.name, include_time_spent=include_time_spent))
