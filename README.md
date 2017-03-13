# Connect Four Master Server

A REST API to connect all the [Connect Four](https://github.com/EpocDotFr/connectfour) players together
from all over the world.

<p align="center">
  <img src="https://raw.githubusercontent.com/EpocDotFr/connectfour-master-server/master/screenshot.png">
</p>

## Features

  - Web-based game browser interface with filtering capabilities
    - Ability to view every single game ever played
    - IP / name / version / status
    - Which player has won if the game is finished
    - When the game has been created, started and finished
  - REST API used by the [Connect Four](https://github.com/EpocDotFr/connectfour) game itself to advertise hosts and keep online game's data up-to-date
    - [More information](https://github.com/EpocDotFr/connectfour-master-server/blob/master/api.md)

## Prerequisites

  - Should work on any Python 3.x version. Feel free to test with another Python version and give me feedback
  - A [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)-capable web server (optional, but recommended)

## Installation

  1. Clone this repo somewhere
  2. `pip install -r requirements.txt`
  3. `export FLASK_APP=cfms.py` (Windows users: `set FLASK_APP=cfms.py`)
  4. `flask create_database` (WARNING: don't re-run this command unless you want to start from scratch, it will wipe out all the data)

## Configuration

Copy the `config.example.py` file to `config.py` and fill in the configuration parameters.

Available configuration parameters are:

  - `SECRET_KEY` Set this to a complex random value
  - `DEBUG` Enable/disable debug mode
  - `LOGGER_HANDLER_POLICY` Policy of the default logging handler

More informations on the three above can be found [here](http://flask.pocoo.org/docs/0.12/config/#builtin-configuration-values).

I'll let you search yourself about how to configure a web server along uWSGI.

## Usage

  - Standalone

Run the internal web server, which will be accessible at `http://localhost:8080`:

```
python local.py
```

Edit this file and change the interface/port as needed.

  - uWSGI

The uWSGI file you'll have to set in your uWSGI configuration is `uwsgi.py`. The callable is `app`.

  - Others

You'll probably have to hack with this application to make it work with one of the solutions described
[here](http://flask.pocoo.org/docs/0.12/deploying/). Send me a pull request if you make it work.

## API docs

Please navigate [here](https://github.com/EpocDotFr/connectfour-master-server/blob/master/api.md) for the full docs.

## How it works

This project is mainly powered by [Flask](http://flask.pocoo.org/) (Python) and [Flask-RESTful](https://flask-restful.readthedocs.io/)
using a small [SQLite](https://en.wikipedia.org/wiki/SQLite) database to persist data. 
[HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol) requests are used to maintain the
games pool up-to-date.

For more information, I suggest you do dive into the code starting with the `cfms.py` file.

## Credits

This project uses GeoLite2 data created by MaxMind, available from [www.maxmind.com](https://www.maxmind.com/).

## End words

If you have questions or problems, you can [submit an issue](https://github.com/EpocDotFr/connectfour-master-server/issues).

You can also submit pull requests. It's open-source man!