from logging.handlers import RotatingFileHandler
from flask_sqlalchemy import SQLAlchemy
from flask_restful import Api
from flask import Flask
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

handler = RotatingFileHandler('storage/logs/errors.log', maxBytes=10000000, backupCount=2)
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
import hooks
