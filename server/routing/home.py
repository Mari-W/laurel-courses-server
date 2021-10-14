from flask import Blueprint, redirect

from server.env import Env
from server.routing.decorators import authorized_route

home_bp = Blueprint("home", __name__, static_folder="../../static")


@home_bp.route('/')
@authorized_route
def home():
    return redirect(Env.get("GITEA_URL"))


@home_bp.route('/favicon.ico')
def favicon():
    return home_bp.send_static_file("favicon.ico")


@home_bp.route('/static/bootstrap.min.css')
def bootstrap():
    return home_bp.send_static_file('bootstrap.min.css')


@home_bp.route('/static/bootstrap.min.css.map')
def bootstrap_map():
    return "not available", 404


@home_bp.route('/static/logo.svg')
def logo():
    return home_bp.send_static_file('logo.svg')
