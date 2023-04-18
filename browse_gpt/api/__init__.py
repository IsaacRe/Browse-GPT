from flask import Flask

from .util import configure_app
from .act_app import bp

def create_app():
    app = Flask(__name__)
    configure_app(app)
    app.register_blueprint(bp)
    return app
