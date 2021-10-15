import traceback

from authlib.integrations.base_client import MismatchingStateError, OAuthError
from flask import session
from telegram import Bot
from werkzeug.exceptions import NotFound
from werkzeug.utils import redirect

from server.env import Env

if Env.get_bool("TELEGRAM_LOGGING", required=False):
    bot = Bot(Env.get("TELEGRAM_TOKEN"))


def error_handling(app):
    @app.errorhandler(NotFound)
    def all_exception_handler(_):
        return "this route does not exist", 404

    @app.errorhandler(MismatchingStateError)
    def state_error(_):
        return redirect("/auth/logout")

    @app.errorhandler(OAuthError)
    def oauth_error(_):
        return redirect("/auth/login")

    if Env.get_bool("TELEGRAM_LOGGING", required=False):
        @app.errorhandler(Exception)
        def all_exception_handler(error):
            send_error(error)


def send_error(exception: Exception):
    text = f"""ERROR occurred on COURSE SERVER

Logged in user: {session.get("user")}

Error: {type(exception).__name__}
Message: {exception}

Stacktrace:
{''.join(traceback.format_tb(exception.__traceback__))}
"""
    print(text)
    if Env.get_bool("TELEGRAM_LOGGING", required=False):
        bot.sendMessage(chat_id=Env.get("TELEGRAM_CHAT_ID"), text=text)


def try_except(try_call, catch_call=None):
    # kinda ugly ikr, but it works :)
    try:
        try_call()
        return True
    except Exception as exception:
        send_error(exception)
        traceback.format_exc()
        if catch_call is not None:
            try:
                catch_call()
            except Exception as exception:
                traceback.format_exc()
                send_error(exception)
    return False
