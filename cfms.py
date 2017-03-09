from flask import Flask, render_template, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import ArrowType
from flask_restful import Api, Resource, abort as abort_restful, marshal_with, fields
from werkzeug.exceptions import HTTPException
from enum import Enum
import logging
import sys
import arrow


# -----------------------------------------------------------
# Boot


app = Flask(__name__, static_url_path='')
app.config.from_pyfile('config.py')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///storage/data/db.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.jinja_env.globals.update(arrow=arrow)

db = SQLAlchemy(app)
api = Api(app)

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
    return render_template('home.html', games=Game.query.get_all())


# -----------------------------------------------------------
# API resources


game_fields = {
    'guid': fields.String,
    'name': fields.String,
    'ip': fields.String,
    'port': fields.Integer,
    'location': fields.String
}


class GamesResource(Resource):
    @marshal_with(game_fields)
    def get(self):
        return Game.query.get_all_waiting()

    def post(self):
        return {}, 201


class GameResource(Resource):
    @marshal_with(game_fields)
    def get(self, guid):
        game = Game.query.get(guid)

        if not game:
            abort_restful(404, message='This game does not exists.')

        return game

    def put(self, guid):
        return {}

    def delete(self, guid):
        game = Game.query.get(guid)

        if not game:
            abort_restful(404, message='This game does not exists.')

        try:
            db.session.delete(game)
            db.session.commit()

            return None, 204
        except Exception as e:
            abort_restful(500, message='Error deleting this game: {}'.format(e))


api.add_resource(GamesResource, '/games')
api.add_resource(GameResource, '/games/<guid>')


# -----------------------------------------------------------
# Models


class GameStatus(Enum):
    WAITING = 'WAITING'
    PLAYING = 'PLAYING'


class Game(db.Model):
    class GameQuery(db.Query):
        def get_all_waiting(self):
            q = self.order_by(Game.name.asc())
            q = q.filter(Game.status == GameStatus.WAITING)

            return q.all()

        def get_all(self):
            q = self.order_by(Game.name.asc())

            return q.all()

    __tablename__ = 'games'
    query_class = GameQuery

    guid = db.Column(db.String(32), primary_key=True, unique=True)

    name = db.Column(db.String(255), nullable=False)
    ip = db.Column(db.String(45), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Enum(GameStatus), default=GameStatus.WAITING)
    location = db.Column(db.String(255), default=None)
    created_at = db.Column(ArrowType, default=arrow.now())

    def __init__(self, guid=None, name=None, ip=None, port=None, status=GameStatus.WAITING, location=None, created_at=arrow.now()):
        self.guid = guid
        self.name = name
        self.ip = ip
        self.port = port
        self.status = status
        self.location = location
        self.created_at = created_at

    def __repr__(self):
        return '<Game> #{} : {}'.format(self.guid, self.name)


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
