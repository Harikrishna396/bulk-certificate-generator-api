import logging
import os
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from .config import load_config
from .db import init_db
from .errors import ApiError
from .routes import bp


def _error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return jsonify(body), status


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.update(load_config(overrides))
    logging.basicConfig(level=logging.INFO)

    os.makedirs(app.config["CERTIFICATE_DIR"], exist_ok=True)
    init_db(app.config["DATABASE_PATH"])
    app.extensions["executor"] = ThreadPoolExecutor(max_workers=app.config["WORKER_THREADS"])
    app.register_blueprint(bp)

    @app.errorhandler(ApiError)
    def handle_api_error(err):
        return _error_response(err.status, err.code, err.message, err.details)

    @app.errorhandler(HTTPException)
    def handle_http_error(err):
        return _error_response(err.code, err.name.lower().replace(" ", "_"), err.description)

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        app.logger.exception("Unhandled error")
        return _error_response(500, "internal_error", "An unexpected error occurred.")

    return app
