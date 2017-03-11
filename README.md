# Connect Four Master Server

A REST API to connect all the [Connect Four](https://github.com/EpocDotFr/connectfour) players from all
over the world.

[TODO screenshot]

## Features

  - Web-based game browser interface with filtering capabilities
  - REST API used by the Connect Four game itself to advertise hosts and keep online game's data up-to-date
  - There's only two features listed but trust me, they are big

## Prerequisites

  - Should work on any Python 3.x version. Feel free to test with another Python version and give me feedback
  - A [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/)-capable web server (optional, but recommended)

## Installation

Clone this repo somewhere and then the usual `pip install -r requirements.txt`.

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

## How it works

This project is mainly powered by [Flask](http://flask.pocoo.org/) (Python) and [Flask-RESTful](https://flask-restful.readthedocs.io/)
using a small [SQLite](https://en.wikipedia.org/wiki/SQLite) database to persist data. 
[HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol) requests are used to maintain the
games pool up-to-date.

For more information, I suggest you do dive into the code starting with the `cfms.py` file.

## Gotchas

As stated above, there's only one very basic security measure in place to prevent anyone to update /
delete any games. There isn't any oAuth or even HTTP authentication. So be aware.

## Credits

This project uses GeoLite2 data created by MaxMind, available from [www.maxmind.com](https://www.maxmind.com/).

## End words

If you have questions or problems, you can [submit an issue](https://github.com/EpocDotFr/connectfour-master-server/issues).

You can also submit pull requests. It's open-source man!