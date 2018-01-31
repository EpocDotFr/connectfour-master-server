from flask import make_response, render_template
from werkzeug.exceptions import HTTPException
from cfms import app


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
