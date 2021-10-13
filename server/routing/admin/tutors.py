import itertools
import json
from json import JSONDecodeError

from flask import Blueprint, render_template, request, redirect

from server.exercises.course import Course
from server.exercises.options import AddTutorOption
from server.integration.gitea_exercises import gitea_exercises
from server.routing.decorators import admin_route

admin_tutors_bp = Blueprint("admin_tutors", __name__)


@admin_tutors_bp.route('/<course>', methods=["GET", "POST"])
@admin_route
def tutors(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    return render_template("admin/tutors.html", course=str(course),
                           tutors=[(tutor, course.get_tutor_student_names(tutor.username))
                                   for tutor in course.tutors])


@admin_tutors_bp.route("/<course>/add", methods=["GET", "POST"])
@admin_route
def add(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if request.method == "GET":
        not_allowed = course.tutor_names + course.student_names
        return render_template("admin/add_tutor.html", course=str(course),
                               users=[user for user in gitea_exercises.get_all_users() if user not in not_allowed])

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "tutor" not in data:
        return "missing info", 500

    if data["tutor"] == "Select tutor":
        return "no tutor was selected", 500

    err = course.add_tutor(data["tutor"], AddTutorOption(
        description=data["description"] if "description" in data and data["description"] else ""))
    if err:
        return err, 500

    return redirect(f"/admin/tutors/{str(course)}")


@admin_tutors_bp.route('/<course>/delete', methods=["POST"])
@admin_route
def delete(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "tutor" not in data:
        return "missing info", 500

    err = course.remove_tutor(data["tutor"])
    if err:
        return err, 500

    return redirect(f"/admin/tutors/{str(course)}")


@admin_tutors_bp.route('/<course>/edit', methods=["GET", "POST"])
@admin_route
def edit(course):
    course = Course.from_str(course)
    if not course:
        return "course not found", 404

    if request.method == "GET":
        return render_template("admin/edit_tutors.html",
                               course=str(course),
                               tutors=json.dumps(
                                   {tutor: course.get_tutor_student_names(tutor)
                                    for tutor in course.tutor_names},
                                   indent=4, sort_keys=True
                               ))

    # check if login attempt is via json data
    data = request.get_json(silent=True)

    # check if user logged in via form data
    if not data:
        data = request.form

    if not data["json"]:
        return "missing json data", 500

    try:
        upd = json.loads(data["json"])
    except JSONDecodeError:
        return "Invalid JSON", 500

    tutors = [tutor.username for tutor in course.tutors]
    students = [student.username for student in course.students]
    students_upd = list(itertools.chain(*[l for l in upd.values() if l]))
    if len(set(students_upd)) != len(students_upd):
        return "JSON contains duplicated tutor assignments for some student", 500

    # every tutor must be mentioned and every student must be assigned exactly once
    # if somebody joined while you edited the json you have to add him

    for tutor in upd.keys():
        if tutor not in tutors:
            return f"JSON contains non existing tutor {tutor}", 500

    for student in students_upd:
        if student not in students:
            return f"JSON contains non existing student {student}", 500

    for tutor in tutors:
        if tutor not in upd.keys():
            return f"JSON did not mention tutor as key {tutor}. " \
                   f"If this is intended, please first remove the tutor from this course or set '{tutor}: null'.", 500

    for student in students:
        if student not in students_upd:
            return f"JSON did not assign a tutor to {student}. " \
                   f"If this is intended, please first remove the student from this course", 500

    course.edit_tutors(upd)

    return redirect(f"/admin/tutors/{str(course)}")
