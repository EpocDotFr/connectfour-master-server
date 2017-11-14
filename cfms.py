from flask import Flask, render_template, make_response, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import ArrowType
from flask_restful import Api, Resource, abort as abort_restful, marshal_with, fields, reqparse
from werkzeug.exceptions import HTTPException
from enum import Enum
from geolite2 import geolite2
import iso3166
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

app.jinja_env.globals.update(arrow=arrow, iso3166=iso3166)

db = SQLAlchemy(app)
api = Api(app, prefix='/api', catch_all_404s=True)

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
    if 'status' in request.args:
        statuses = request.args.getlist('status')
    else:
        statuses = [GameStatus.WAITING.value]

    name = request.args.get('name')
    country = request.args.get('country')

    return render_template(
        'home.html',
        games=Game.query.get_all_for_home(statuses=[GameStatus(status) for status in statuses], name=name, country=country),
        statuses=statuses
    )


# -----------------------------------------------------------
# API resources


def game_status(value):
    valid_values = [GameStatus.PLAYING, GameStatus.FINISHED]

    try:
        value = GameStatus(value)

        if value not in valid_values:
            raise ValueError()
    except ValueError:
        raise ValueError('Invalid parameter. It can be one of: {}'.format(', '.join([e.value for e in valid_values])))

    return value


def game_winner(value):
    try:
        value = GameWinner(value)
    except ValueError:
        raise ValueError('Invalid parameter. It can be one of: {}'.format(', '.join([e.value for e in GameWinner])))

    return value


def country(value):
    if value not in iso3166.countries_by_alpha2:
        raise ValueError('Invalid parameter. It must be a valid ISO 3166-1 alpha-2 country code.')

    return value


class EnumField(fields.Raw):
    def format(self, enum):
        return enum.value


get_games_parser = reqparse.RequestParser()
get_games_parser.add_argument('version', required=True, location='args')
get_games_parser.add_argument('country', location='args', type=country)
get_games_parser.add_argument('name', location='args')

post_games_parser = reqparse.RequestParser()
post_games_parser.add_argument('name', required=True, location='json')
post_games_parser.add_argument('version', required=True, location='json')

put_game_parser = reqparse.RequestParser()
put_game_parser.add_argument('name', location='json')
put_game_parser.add_argument('version', location='json')
put_game_parser.add_argument('token', required=True, location='json')
put_game_parser.add_argument('status', location='json', type=game_status)
put_game_parser.add_argument('winner', location='json', type=game_winner)

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

        return Game.query.get_all_for_api(version=args['version'], country=args['country'], name=args['name'])

    @marshal_with(private_game_fields)
    def post(self):
        args = post_games_parser.parse_args()

        game = Game()
        game.token = uuid.uuid4().hex
        game.name = args['name']
        game.ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        game.version = args['version']

        with geolite2 as gl2:
            location = gl2.reader().get(game.ip)

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

        if game.status == GameStatus.FINISHED:
            abort_restful(403, message='This game can no longer be updated.')

        args = put_game_parser.parse_args()

        if args['token'] != game.token:
            abort_restful(403, message='You are not allowed to perform this operation.')

        if args['status']:
            if args['status'] == game.status:
                abort_restful(400, message='This game already has the {} status.'.format(args['status']))

            game.status = GameStatus(args['status'])

            if game.status == GameStatus.PLAYING:
                game.started_at = arrow.now()
            elif game.status == GameStatus.FINISHED:
                game.finished_at = arrow.now()
                game.winner = args['winner']

        if args['name']:
            game.name = args['name']

        if args['version']:
            game.version = args['version']

        game.last_ping_at = arrow.now()

        ip = request.headers.get('X-Forwarded-For', request.remote_addr)

        if ip != game.ip:
            game.ip = ip

            with geolite2 as gl2:
                location = gl2.reader().get(game.ip)

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

        if game.status == GameStatus.FINISHED:
            abort_restful(403, message='This game can no longer be deleted.')

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
        def get_all_for_api(self, version, country=None, name=None):
            q = self.order_by(Game.last_ping_at.asc())
            q = q.order_by(Game.name.asc())
            q = q.filter(Game.status == GameStatus.WAITING and Game.version == version)

            if country:
                q = q.filter(Game.country == country)

            if name:
                q = q.filter(Game.name.like('%' + name + '%'))

            return q.all()

        def get_all_for_home(self, statuses=None, country=None, name=None):
            q = self.order_by(Game.last_ping_at.asc())
            q = q.order_by(Game.name.asc())

            if statuses:
                q = q.filter(Game.status.in_(statuses))

            if country:
                q = q.filter(Game.country == country)

            if name:
                q = q.filter(Game.name.like('%' + name + '%'))

            return q.all()

        def get_all_old(self, ttl):
            q = self.filter(Game.last_ping_at <= arrow.now().replace(minutes=-ttl))
            q = q.filter(Game.status != GameStatus.FINISHED)

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

        country = iso3166.countries.get(self.country)

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


@app.cli.command()
def clean():
    """Delete all old games."""

    ttl = app.config['GAMES_TTL']

    app.logger.info('Getting all games olders than {} minutes'.format(ttl))

    games = Game.query.get_all_old(ttl=ttl)

    app.logger.info('Deleting {} games'.format(len(games)))

    try:
        for game in games:
            db.session.delete(game)

        db.session.commit()

        app.logger.info('Done')
    except Exception as e:
        app.logger.error(e)


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
