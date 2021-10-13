import os
from datetime import timedelta

from flask import Flask
from werkzeug.security import gen_salt

from server.database import database
from server.error_handling import error_handling
from server.oauth import init_oauth
from server.routing.admin.admin import admin_bp
from server.routing.admin.courses import admin_courses_bp
from server.routing.admin.exercises import admin_exercises_bp
from server.routing.admin.students import admin_students_bp
from server.routing.admin.tutors import admin_tutors_bp
from server.routing.api import api_bp
from server.routing.auth import auth_bp
from server.routing.cli import cli_bp
from server.routing.courses import courses_bp
from server.routing.home import home_bp
from server.routing.hooks import hooks_bp


def create_app():
    # init server
    app = Flask(__name__, template_folder="../templates")
    app.config.update(os.environ)

    # some dynamic settings
    app.config["SECRET_KEY"] = gen_salt(32)
    app.config["SESSION_PERMANENT"] = True
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=100)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # init database
    @app.before_first_request
    def create_tables():
        database.alchemy.create_all()

    database.alchemy.init_app(app)

    # add routers
    app.register_blueprint(home_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(courses_bp, url_prefix='/courses')
    app.register_blueprint(hooks_bp, url_prefix='/hooks')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(cli_bp, url_prefix='/cli')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(admin_courses_bp, url_prefix='/admin/courses')
    app.register_blueprint(admin_tutors_bp, url_prefix='/admin/tutors')
    app.register_blueprint(admin_exercises_bp, url_prefix='/admin/exercises')
    app.register_blueprint(admin_students_bp, url_prefix='/admin/students')

    # setup error handling
    error_handling(app)

    # init oauth client
    init_oauth(app)

    return app
