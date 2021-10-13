from server.env import Env

Env.init()


# load env before importing create_app
# as this creates stuff already reading from
# env file >.<
def run():
    from server.app import create_app
    return create_app()


app = run()
