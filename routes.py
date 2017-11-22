from flask_restful import Resource, abort as abort_restful, marshal_with, fields, reqparse
from flask import request, render_template
from geolite2 import geolite2
from models import *
from cfms import app, api
import uuid


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
