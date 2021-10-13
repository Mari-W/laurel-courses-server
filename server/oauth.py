from authlib.integrations.flask_client import OAuth

from server.env import Env

oauth = OAuth()


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        'auth',
        server_metadata_url=f"{Env.get('AUTH_LOCAL_URL')}/.well-known/openid-configuration",
        client_kwargs={
            'scope': 'openid email profile'
        },
        client_id=Env.get("CLIENT_ID"),
        client_secret=Env.get("CLIENT_SECRET")
    )
