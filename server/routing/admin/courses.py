from flask import Blueprint, render_template, request, redirect, session

from server.exercises.course import Course
from server.exercises.models import CourseEntity
from server.integration.gitea_exercises import CreateCourseOption, gitea_exercises
from server.routing.decorators import admin_route

admin_courses_bp = Blueprint("admin_courses", __name__)


@admin_courses_bp.route('/', methods=["GET", "POST"])
@admin_route
def courses():
    return render_template("admin/courses.html", courses=CourseEntity.query.all())


@admin_courses_bp.route("/add", methods=["GET", "POST"])
@admin_route
def add():
    if request.method == "GET":
        return render_template("admin/add_course.html")

    # allow json requests
    data = request.get_json(silent=True)

    if not data:
        data = request.form

    if "name" not in data or "semester" not in data:
        return "missing info", 500

    course = Course(name=data["name"], semester=data["semester"])

    if not course.is_valid:
        return "name or semester does not meet the formatting requirements", 500

    if not gitea_exercises.user_exists(session.get("user")["sub"]):
        return "cannot create course without ever logging into gitea"

    opts = CreateCourseOption(
        display_name=data["display_name"] if "display_name" in data and data["display_name"] != "" else str(course),
        website=data["website"] if "website" in data and data["website"] != "" else "https://uni-freiburg.de",
        joinable='joinable' in data and data['joinable'] == 'on',
        owner=session.get("user")["sub"]
    )

    err = course.create(opts)
    if err:
        return err, 500

    return redirect("/admin/courses")


@admin_courses_bp.route('/delete', methods=["POST"])
@admin_route
def delete():
    course = Course.from_req()
    if not course:
        return "course not found", 404

    err = course.delete()
    if err:
        return err, 500

    return redirect("/admin/courses")


@admin_courses_bp.route('/close', methods=["POST"])
@admin_route
def close():
    course = Course.from_req()
    if not course:
        return "course not found", 404

    err = course.close()
    if err:
        return err, 500

    return redirect("/admin/courses")


@admin_courses_bp.route('/open', methods=["POST"])
@admin_route
def open():
    course = Course.from_req()
    if not course:
        return "course not found", 404

    if course.is_restricted:
        return "course is in restricted mode", 500

    err = course.open()
    if err:
        return err, 500

    return redirect("/admin/courses")


@admin_courses_bp.route('/restrict', methods=["POST"])
@admin_route
def restrict():
    course = Course.from_req()
    if not course:
        return "course not found", 404

    err = course.close()
    if err:
        return err, 500

    err = course.restrict_student_access()
    if err:
        return err, 500

    return redirect("/admin/courses")


@admin_courses_bp.route('/permit', methods=["POST"])
@admin_route
def permit():
    course = Course.from_req()
    if not course:
        return "course not found", 404

    err = course.permit_student_access()
    if err:
        return err, 500

    return redirect("/admin/courses")
