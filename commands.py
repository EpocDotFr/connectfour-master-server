from cfms import app, db
from models import *
import click


@app.cli.command()
def create_database():
    """Delete then create all the database tables."""
    if not click.confirm('Are you sure?'):
        click.secho('Aborted', fg='red')

        return

    click.echo('Dropping everything')

    db.drop_all()

    click.echo('Creating tables')

    db.create_all()

    click.secho('Done', fg='green')


@app.cli.command()
def clean():
    """Delete all old games."""
    ttl = app.config['GAMES_TTL']

    click.echo('Getting all games olders than {} minutes'.format(ttl))

    games = Game.query.get_all_old(ttl=ttl)

    click.echo('Deleting {} games'.format(len(games)))

    try:
        for game in games:
            db.session.delete(game)

        db.session.commit()

        click.secho('Done', fg='green')
    except Exception as e:
        click.echo(e, err=True)
