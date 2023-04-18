from flask import Blueprint, request, current_app


bp = Blueprint("act_app", __name__)


@bp.route("/", methods=["GET"])
def root():
    return ""


@bp.route("/override", methods=["POST"])
def override_route():
    pass


@bp.route("/query", methods=["POST"])
def query_endpoint():
    pass
