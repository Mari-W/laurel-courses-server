# from io import BytesIO

from datetime import datetime
from flask import Blueprint, jsonify, request

from server.exercises.course import Course
from server.integration.auth_server import auth
from server.util.stats import StatsTable

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

    return jsonify(
        {tutor: course.get_tutor_student_names(tutor) for tutor in course.tutor_names}
    )


@api_bp.route("/course/<course>/is_tutor/<tutor>", methods=["GET"])
@admin_route
def is_tutor(course, tutor):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if not course.has_tutor(tutor):
        return "not a tutor", 404
    return "", 200


@api_bp.route("/course/<course>/is_student/<student>", methods=["GET"])
@admin_route
def is_student(course, student):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if not course.has_student(student):
        return "not a student", 404
    return "", 200


@api_bp.route("/course/<course>/exercises", methods=["GET"])
@admin_route
def exercises(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return jsonify(
        [
            {
                "name": exercise.name,
                "points": exercise.points,
                "start": exercise.start.isoformat(),
                "end": exercise.end.isoformat(),
            }
            for exercise in course.finished_exercises
        ]
    )


@api_bp.route("/course/<course>/students", methods=["GET"])
@admin_route
def students(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return jsonify({student.username: student.to_dict() for student in course.students})


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
            "matrikelnummer": users[student.username]["matrikelnummer"]
            if student.username in users
            else None,
            **course.get_student_exercises_stats(
                student.username, exercises=exercises, include_ungraded=include_ungraded
            ),
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

    include_time_spent = "include_time_spent" in request.args

    return jsonify(
        course.get_exercise_stats(exercise.name, include_time_spent=include_time_spent)
    )


@api_bp.route("/course/<course>/exercises/stats.md", methods=["GET"])
@admin_route
def exercise_tables(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404
    points_table = StatsTable()
    time_spent_table = StatsTable()
    now = datetime.now()
    md = f"# {course.name}: Exercise Stats\n\n"
    for exercise in course.finished_exercises:
        if exercise.end < now:
            res = course.get_exercise_stats(exercise.name, include_time_spent=True)
            students_points = [
                v["points"]
                for v in res["students"].values()
                if "points" in v and v["points"] and "tutor" in v and v["tutor"]
            ]
        if students_points:
            points_table.add_row(exercise.name, students_points)

        students_time_spent = [
            v["time_spent"]
            for v in res["students"].values()
            if "time_spent" in v and v["time_spent"]
        ]
        if students_time_spent:
            time_spent_table.add_row(exercise.name, students_time_spent)

    try:
        s = points_table.to_table().to_markdown_str(formatter=points_table.formatter())
        md += "### Point Distribution\n\n"
        md += s + "\n\n"
    except ZeroDivisionError:
        pass

    try:
        s = time_spent_table.to_table().to_markdown_str(
            formatter=time_spent_table.formatter()
        )
        md += "### Time Distribution\n\n"
        md += s + "\n"
    except ZeroDivisionError:
        pass

    return md.replace("\n", "<br>"), 200
