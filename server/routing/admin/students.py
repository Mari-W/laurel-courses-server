import itertools
import json
from datetime import datetime
from json import JSONDecodeError

from flask import Blueprint, render_template, request, redirect, session

from server.exercises.course import Course
from server.exercises.options import AddTutorOption, CreateExerciseOption
from server.integration.gitea_exercises import gitea_exercises
from server.routing.decorators import admin_route

admin_students_bp = Blueprint("admin_students", __name__)


@admin_students_bp.route('/<course>', methods=["GET", "POST"])
@admin_route
def exercises(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return render_template("admin/students.html", course=str(course),
                           students=course.students)


@admin_students_bp.route('/<course>/delete', methods=["POST"])
@admin_route
def delete(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "student" not in data:
        return "missing info", 500

    err = course.remove_student(data["student"])
    if err:
        return err, 500

    return redirect(f"/admin/students/{str(course)}")
