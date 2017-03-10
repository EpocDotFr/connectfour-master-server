from flask import Flask, render_template, make_response, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import ArrowType
from flask_restful import Api, Resource, abort as abort_restful, marshal_with, fields, reqparse
from werkzeug.exceptions import HTTPException
from enum import Enum
from geolite2 import geolite2
from iso3166 import countries
import logging
import sys
import arrow


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage/data/db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['BUNDLE_ERRORS'] = True

app.jinja_env.globals.update(arrow=arrow)

db = SQLAlchemy(app)
api = Api(app, catch_all_404s=True)

# Default Python logger
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    stream=sys.stdout
)

logging.getLogger().setLevel(logging.INFO)

# Default Flask loggers
for handler in app.logger.handlers:
    handler.setFormatter(logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s', datefmt='%d/%m/%Y %H:%M:%S'))


# -----------------------------------------------------------
# Routes


get_games_parser = reqparse.RequestParser()
get_games_parser.add_argument('version', required=True, location='args')

post_games_parser = reqparse.RequestParser()
post_games_parser.add_argument('name', required=True, location='json')
post_games_parser.add_argument('version', required=True, location='json')


@app.route('/')
def home():
    return render_template('home.html', games=Game.query.get_all_for_home())


# -----------------------------------------------------------
# API resources


game_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'ip': fields.String,
    'country_name': fields.String,
    'created_at': fields.String
}


class GamesResource(Resource):
    @marshal_with(game_fields)
    def get(self):
        args = get_games_parser.parse_args()

        return Game.query.get_all_for_api(version=args['version'])

    @marshal_with(game_fields)
    def post(self):
        args = post_games_parser.parse_args()

        game = Game()
        game.name = args['name']
        game.ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        game.version = args['version']

        geolite2_reader = geolite2.reader()
        location = geolite2_reader.get(game.ip)
        geolite2_reader.close()

        if location:
            game.country = location['country']['names']['en'] # FIXME

        try:
            db.session.add(game)
            db.session.commit()

            return game, 201
        except Exception as e:
            abort_restful(500, message='Error creating this game: {}'.format(e))


class GameResource(Resource):
    @marshal_with(game_fields)
    def get(self, id):
        game = Game.query.get(id)

        if not game:
            abort_restful(404, message='This game does not exists.')

        return game

    def put(self, id):
        return {}

    def delete(self, id):
        game = Game.query.get(id)

        if not game:
            abort_restful(404, message='This game does not exists.')

        try:
            db.session.delete(game)
            db.session.commit()

            return None, 204
        except Exception as e:
            abort_restful(500, message='Error deleting this game: {}'.format(e))


api.add_resource(GamesResource, '/games')
api.add_resource(GameResource, '/games/<id>')


# -----------------------------------------------------------
# Models


class GameStatus(Enum):
    WAITING = 'WAITING'
    PLAYING = 'PLAYING'
    FINISHED = 'FINISHED'


class Game(db.Model):
    class GameQuery(db.Query):
        def get_all_for_api(self, version):
            q = self.order_by(Game.name.asc())
            q = q.filter(Game.status == GameStatus.WAITING and Game.version == version)

            return q.all()

        def get_all_for_home(self):
            q = self.order_by(Game.name.asc())

            return q.all()

    __tablename__ = 'games'
    query_class = GameQuery

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)

    name = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(45), nullable=False, unique=True)
    country = db.Column(db.String(255), default=None)
    version = db.Column(db.String(10), nullable=False)
    status = db.Column(db.Enum(GameStatus), default=GameStatus.WAITING)
    created_at = db.Column(ArrowType, default=arrow.now())
    started_at = db.Column(ArrowType, default=None)
    finished_at = db.Column(ArrowType, default=None)

    def __init__(self, name=None, ip=None, country=None, version=None, status=GameStatus.WAITING, created_at=arrow.now(), started_at=None, finished_at=None):
        self.name = name
        self.ip = ip
        self.country = country
        self.version = version
        self.status = status
        self.created_at = created_at
        self.started_at = started_at
        self.finished_at = finished_at

    def __repr__(self):
        return '<Game> #{} : {}'.format(self.id, self.name)

    @property
    def status_text(self):
        if self.status == GameStatus.WAITING:
            return 'Waiting'
        elif self.status == GameStatus.PLAYING:
            return 'Playing'
        elif self.status == GameStatus.FINISHED:
            return 'Finished'

    @property
    def country_name(self):
        country = countries.get(self.country)

        if country:
            return country.name
        else:
            return 'Unknow'


# -----------------------------------------------------------
# CLI commands


@app.cli.command()
def create_database():
    """Delete then create all the database tables."""
    db.drop_all()
    db.create_all()


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
