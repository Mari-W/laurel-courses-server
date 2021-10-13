from flask import Blueprint, redirect

from server.routing.decorators import admin_route

admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/", methods=["GET"])
@admin_route
def homepage():
    return redirect("/admin/courses")
