import itertools
import json
from datetime import datetime
from json import JSONDecodeError

from flask import Blueprint, render_template, request, redirect, session

from server.exercises.course import Course
from server.exercises.options import AddTutorOption, CreateExerciseOption
from server.integration.gitea_exercises import gitea_exercises
from server.routing.decorators import admin_route

admin_exercises_bp = Blueprint("admin_exercises", __name__)


@admin_exercises_bp.route('/<course>', methods=["GET", "POST"])
@admin_route
def exercises(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return render_template("admin/exercises.html", course=str(course),
                           exercises=course.exercises)


@admin_exercises_bp.route("/<course>/add", methods=["GET", "POST"])
@admin_route
def add(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if request.method == "GET":
        return render_template("admin/add_exercise.html", course=str(course))

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "name" not in data or "start_date" not in data or "end_date" not in data or "points" not in data:
        return "missing info", 500

    name = data["name"].strip()

    try:
        end = datetime.strptime(data["end_date"], "%Y-%m-%dT%H:%M")
        start = datetime.strptime(data["start_date"], "%Y-%m-%dT%H:%M")
        try:
            points = int(data["points"].strip())
        except ValueError:
            points = float(data["points"].strip())
    except ValueError:
        return "Could not parse start or end date, or points is not a number", 500

    err = course.add_exercise(name, CreateExerciseOption(
        creator=session.get("user")["sub"],
        start=start,
        end=end,
        points=points,
    ))
    if err:
        return err, 500

    return redirect(f"/admin/exercises/{str(course)}")


@admin_exercises_bp.route('/<course>/delete', methods=["POST"])
@admin_route
def delete(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "exercise" not in data:
        return "missing info", 500

    err = course.delete_exercise(data["exercise"])
    if err:
        return err, 500

    return redirect(f"/admin/exercises/{str(course)}")


@admin_exercises_bp.route('/<course>/<exercise>/edit', methods=["GET", "POST"])
@admin_route
def edit(course, exercise):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if not course.has_exercise(exercise):
        return "exercise not found", 404

    exercise = course.get_exercise(exercise)

    if request.method == "GET":
        start = exercise.start.strftime("%Y-%m-%dT%H:%M")
        end = exercise.end.strftime("%Y-%m-%dT%H:%M")
        return render_template("admin/edit_exercise.html", exercise=exercise, start=start, end=end)

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "start_date" not in data or "end_date" not in data or "points" not in data:
        return "missing info", 500

    try:
        end = datetime.strptime(data["end_date"], "%Y-%m-%dT%H:%M")
        start = datetime.strptime(data["start_date"], "%Y-%m-%dT%H:%M")
        points = float(data["points"].strip())
    except ValueError:
        return "could not parse start or end date, or points is not a float", 500

    if start != exercise.start:
        course.update_start_date(exercise.name, start)

    if end != exercise.end:
        course.update_end_date(exercise.name, end)

    if points != exercise.points:
        course.update_points(exercise.name, points)

    return redirect(f"/admin/exercises/{str(course)}")
