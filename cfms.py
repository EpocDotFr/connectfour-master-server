from flask import Flask, render_template, make_response, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import ArrowType
from flask_restful import Api, Resource, abort as abort_restful, marshal_with, fields, reqparse
from werkzeug.exceptions import HTTPException
from enum import Enum
from geolite2 import geolite2
from iso3166 import countries
from flask_babel import Babel
import uuid
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
Babel(app)

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


@app.route('/')
def home():
    return render_template('home.html', games=Game.query.get_all_for_home())


# -----------------------------------------------------------
# API resources


def game_status(value):
    valid_values = [GameStatus.PLAYING.value, GameStatus.FINISHED.value]

    if value not in valid_values:
        raise ValueError('Invalid parameter. It can be one of: {}'.format(', '.join(valid_values)))

    return value


def game_winner(value):
    valid_values = [GameWinner.RED.value, GameWinner.YELLOW.value]

    if value not in valid_values:
        raise ValueError('Invalid parameter. It can be one of: {}'.format(', '.join(valid_values)))

    return value


class EnumField(fields.Raw):
    def format(self, enum):
        return enum.value


get_games_parser = reqparse.RequestParser()
get_games_parser.add_argument('version', required=True, location='args')

post_games_parser = reqparse.RequestParser()
post_games_parser.add_argument('name', required=True, location='json')
post_games_parser.add_argument('version', required=True, location='json')

put_game_parser = reqparse.RequestParser()
put_game_parser.add_argument('name', location='json')
put_game_parser.add_argument('version', location='json')
put_game_parser.add_argument('token', required=True, location='json')
put_game_parser.add_argument('status', location='json', type=game_status)
put_game_parser.add_argument('winner', location='json', type=game_winner)
put_game_parser.add_argument('ping', location='json', type=bool)

delete_game_parser = reqparse.RequestParser()
delete_game_parser.add_argument('token', required=True, location='json')

public_game_fields = {
    'id': fields.Integer,
    'name': fields.String,
    'ip': fields.String,
    'country': fields.String,
    'version': fields.String,
    'status': EnumField(),
    'created_at': fields.String,
    'started_at': fields.String,
    'finished_at': fields.String,
    'winner': EnumField()
}

private_game_fields = {
    **public_game_fields,
    **{
        'token': fields.String
    }
}


class GamesResource(Resource):
    @marshal_with(public_game_fields)
    def get(self):
        args = get_games_parser.parse_args()

        return Game.query.get_all_for_api(version=args['version'])

    @marshal_with(private_game_fields)
    def post(self):
        args = post_games_parser.parse_args()

        game = Game()
        game.token = uuid.uuid4().hex
        game.name = args['name']
        game.ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        game.version = args['version']

        geolite2_reader = geolite2.reader()
        location = geolite2_reader.get(game.ip)
        geolite2_reader.close()

        if location:
            game.country = location['country']['iso_code']

        try:
            db.session.add(game)
            db.session.commit()

            return game, 201
        except Exception as e:
            abort_restful(500, message='Error creating this game: {}'.format(e))


class GameResource(Resource):
    def _get_game(self, id):
        game = Game.query.get(id)

        if not game:
            abort_restful(404, message='This game does not exists.')

        return game

    @marshal_with(public_game_fields)
    def get(self, id):
        return self._get_game(id)

    @marshal_with(public_game_fields)
    def put(self, id):
        game = self._get_game(id)

        args = put_game_parser.parse_args()

        if args['token'] != game.token:
            abort_restful(403, message='You are not allowed to perform this operation.')

        if args['status']:
            if args['status'] == game.status:
                abort_restful(400, message='This game already has the {} status.'.format(args['status']))

            game.status = args['status']

            if game.status == GameStatus.PLAYING.value:
                game.started_at = arrow.now()
            elif game.status == GameStatus.FINISHED.value:
                game.finished_at = arrow.now()
                game.winner = args['winner']

        if args['name']:
            game.name = args['name']

        if args['version']:
            game.version = args['version']

        if args['ping']:
            game.last_ping_at = arrow.now()

        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if ip != game.ip:
            game.ip = ip

            geolite2_reader = geolite2.reader()
            location = geolite2_reader.get(game.ip)
            geolite2_reader.close()

            if location:
                game.country = location['country']['iso_code']

        try:
            db.session.add(game)
            db.session.commit()

            return game, 200
        except Exception as e:
            abort_restful(500, message='Error updating this game: {}'.format(e))

    def delete(self, id):
        game = self._get_game(id)

        args = delete_game_parser.parse_args()

        if args['token'] != game.token:
            abort_restful(403, message='You are not allowed to perform this operation.')

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


class GameWinner(Enum):
    RED = 'RED'
    YELLOW = 'YELLOW'


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

    token = db.Column(db.String(32), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(45), nullable=False, unique=True)
    country = db.Column(db.String(255), default=None)
    version = db.Column(db.String(10), nullable=False)
    status = db.Column(db.Enum(GameStatus), default=GameStatus.WAITING)
    winner = db.Column(db.Enum(GameWinner), default=None)
    last_ping_at = db.Column(ArrowType, default=arrow.now())
    created_at = db.Column(ArrowType, default=arrow.now())
    started_at = db.Column(ArrowType, default=None)
    finished_at = db.Column(ArrowType, default=None)

    def __init__(self, name=None, ip=None, country=None, version=None, status=GameStatus.WAITING, winner=None, last_ping_at=arrow.now(), created_at=arrow.now(), started_at=None, finished_at=None):
        self.name = name
        self.ip = ip
        self.country = country
        self.version = version
        self.status = status
        self.winner = winner
        self.last_ping_at = last_ping_at
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
    def winner_text(self):
        if self.winner == GameWinner.RED:
            return 'Red'
        if self.winner == GameWinner.YELLOW:
            return 'Yellow'

    @property
    def country_name(self):
        if not self.country:
            return None

        country = countries.get(self.country)

        if country:
            return country.name
        else:
            return None


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
