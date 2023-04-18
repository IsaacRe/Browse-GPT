from flask import Flask

from ..config import BrowingSessionConfig


def configure_app(app: Flask):
    app.config["sess_cfg"] = BrowingSessionConfig.parse_args(allow_unknown=True)
