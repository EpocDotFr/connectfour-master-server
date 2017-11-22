from sqlalchemy_utils import ArrowType
from enum import Enum
from cfms import db
import iso3166
import arrow

__all__ = [
    'GameStatus',
    'GameWinner',
    'Game'
]


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
            q = self.filter(Game.last_ping_at <= arrow.now().shift(minutes=-ttl))
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
