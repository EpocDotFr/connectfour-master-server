from flask import Flask, make_response, render_template
from logging.handlers import RotatingFileHandler
from werkzeug.exceptions import HTTPException
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
import iso3166
import logging
import arrow


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['LOGGER_HANDLER_POLICY'] = 'production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage/data/db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BUNDLE_ERRORS'] = True

db = SQLAlchemy(app)
api = Api(app, prefix='/api', catch_all_404s=True)

handler = RotatingFileHandler('storage/logs/errors.log', maxBytes=25000, backupCount=2)
handler.setLevel(logging.WARNING)
formatter = logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

app.jinja_env.globals.update(arrow=arrow, iso3166=iso3166)

# -----------------------------------------------------------
# After-init imports


import routes
import models
import commands


# -----------------------------------------------------------
# HTTP errors handler


@app.errorhandler(401)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(500)
@app.errorhandler(503)
def http_error_handler(error, without_code=False):
    if isinstance(error, HTTPException):
        error = error.code
    elif not isinstance(error, int):
        error = 500

    body = render_template('errors/{}.html'.format(error))

    if not without_code:
        return make_response(body, error)
    else:
        return make_response(body)
