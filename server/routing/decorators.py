import functools

from flask import session, request, redirect

from server.env import Env
from server.routing.auth import cors


def authorized_route(f):
    @functools.wraps(f)
    def decorated_function(*args, **kws):
        if not session.get("user"):
            session["redirect"] = request.url.replace(Env.get('PUBLIC_URL'), '')
            return cors(redirect("/auth/login"))
        return f(*args, **kws)

    return decorated_function


def admin_route(f):
    @functools.wraps(f)
    def decorated_function(*args, **kws):
        if request.headers.get("Authorization") != Env.get("API_KEY"):
            if not session.get("user"):
                return "unauthorized", 403
            if session.get("user")["role"] != "admin":
                return "unauthorized", 403
        return f(*args, **kws)

    return decorated_function
