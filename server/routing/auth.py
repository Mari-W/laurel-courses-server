from flask import Blueprint, session, request, redirect, Response
from server.env import Env
from server.oauth import oauth

auth_bp = Blueprint("auth", __name__)


def cors(r: Response):
    origin = request.headers.get('Referer')
    if not origin:
        origin = request.headers.get('Origin')
    if origin:
        return r

    r.headers.add('Access-Control-Allow-Origin', origin.rstrip("/"))
    r.headers.add("Access-Control-Allow-Headers", "*")
    r.headers.add("Access-Control-Allow-Credentials", "true")
    r.headers.add("Access-Control-Allow-Methods", "GET,POST")
    return r


@auth_bp.route('/login')
def login():
    if "redirect" in request.args:
        session["redirect"] = request.args["redirect"]
    return cors(oauth.auth.authorize_redirect(Env.get("PUBLIC_URL") + "/auth/callback"))


@auth_bp.route('/callback')
def callback():
    token = oauth.auth.authorize_access_token()
    user = oauth.auth.parse_id_token(token)

    if not user:
        return "Failed to authenticate", 500

    session['user'] = user
    session.permanent = True

    return cors(redirect(session.pop('redirect')) if "redirect" in session else redirect("/"))


@auth_bp.route('/logout')
def logout():
    session.pop("user", None)
    redirect_url = request.args["redirect"] if "redirect" in request.args.keys() else Env.get("PUBLIC_URL")
    return cors(redirect(f"{Env.get('AUTH_URL')}/auth/logout?redirect={redirect_url}"))
