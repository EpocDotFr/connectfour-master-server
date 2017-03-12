# Connect Four Master Server API documentation

The Connect Four Master Server (CFMS) provide a simple REST API used by the [Connect Four](https://github.com/EpocDotFr/connectfour)
game itself to advertise hosts and keep online game's data up-to-date.

## Endpoint

Let's say we installed the CFMS under the `games.example.com` domain. The web-based game browser
interface will be available right under this domain. Thus, the API endpoint will be `games.example.com/api`.

## Authentication

*There isn't any authentication / authorization method in place.* There's only one very basic security
measure to prevent anyone to update / delete any games. So be aware.

Continue reading to read more.

## HTTP status codes

The HTTP response status code must be used to check if the sent request was successfully handled or not:

  - 2xx: Everything is OK. The response body will contain whatever the resource provide (check its doc)
  - 4xx: The client made a mistake in its request, typically it's an input parameters validation error
  - 5xx: There were a server error

Read below to know what kind of output (and input) you can get in those different cases.

## Input and output data format

Everything is [JSON](https://en.wikipedia.org/wiki/JSON). You'll `PUT` or `POST` JSON data in the HTTP
request body, and the API will give you JSON data in the HTTP response body.

### Input

When a resource says "I'm a `PUT` resource and I want the `hey` and `blow` input parameters", you'll
have to send them this way in the HTTP request body:

```json
{
    "hey": "awesome",
    "blow": "hey"
}
```

Some resource can however require parameters in the query string. Carefuly read their doc.

### Output

You can get 3 different types of output regarding the HTTP response status code (read above for the
available ones).

#### Success (2xx)

The output can be different regarding the resource. It can be a HTTP response code `204` (no content).
It can be a `200` or `201` with JSON output. Read the resource doc.

#### Client error (4xx)

Typically an input parameters validation error.

```json
{
    "message": {
        "blow": "Missing required parameter in the JSON body",
        "hey": "Missing required parameter in the JSON body"
    }
}
```

In this case the `hey` and `blow` input parameters are missing.

If a query string parameter is misisng or invalid, it's the same output:

```json
{
    "message": {
        "active": "Missing required parameter in the query string"
    }
}
```

#### Server error (5xx)

They should not happen.

Example:

```json
{
    "message": "Error creating this thing: (sqlite3.IntegrityError) UNIQUE constraint failed: thing.thingy"
}
```