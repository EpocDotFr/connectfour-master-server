# Connect Four Master Server API documentation

The Connect Four Master Server (CFMS) provide a simple REST API used by the [Connect Four](https://github.com/EpocDotFr/connectfour)
game itself to advertise hosts and keep online game's data up-to-date.

## Endpoint

Let's say we installed the CFMS under the `games.example.com` domain. The web-based game browser
interface will be available right under this domain. Thus, the API endpoint will be `games.example.com/api`.

## Authentication

**There isn't any authentication / authorization method in place.** There's only one very basic security
measure to prevent anyone to update / delete any games. So be aware.

Continue reading to read more.

## HTTP status codes

The HTTP response status code must be used to check if the sent request was successfully handled or not:

  - `2xx` Everything is OK. The response body will contain whatever the resource provide (check its doc)
  - `4xx` The client made a mistake in its request, typically it's an input parameters validation error
  - `5xx` There were a server error

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

#### Success (`2xx`)

The output can be different regarding the resource. It can be a HTTP response code `204` (no content).
It can be a `200` or `201` with JSON output. Read the resource doc.

#### Client error (`4xx`)

Typically an input parameters validation error:

```json
{
    "message": {
        "blow": "Missing required parameter in the JSON body",
        "hey": "Missing required parameter in the JSON body"
    }
}
```

In this case the `hey` and `blow` input parameters are missing.

If a query string parameter is missing or invalid, it's the same output:

```json
{
    "message": {
        "active": "Missing required parameter in the query string"
    }
}
```

May also happen in other cases like the requested resource wasn't found:

```json
{
    "message": "This thing does not exists."
}
```

#### Server error (`5xx`)

They should not happen.

Example:

```json
{
    "message": "Error creating this thing: (sqlite3.IntegrityError) UNIQUE constraint failed: thing.thingy"
}
```

## Resources

Here's the interesting part of this doc. For readability reasons, I'll not prepend resources URI with
the API endpoint.

### `/games`

Provide ways to manipulate games collection.

#### `GET`

Return a collection (array) of waiting games matching a Connect Four version along a `200`. An empty
array is returned if no games are matching these criteria.

##### Parameters

  - Query string
    - `version` (string) (**required**) - A Connect Four version i.e `1.0`

#### `POST`

Create a new game and return it along a `201`. A unique token is returned along the game's data if created
successfully: this token will be required for any future critical operation on this game (`DELETE` and
`PUT`). **This token will only be issued once**, so be sure to put it somewhere in a variable.

##### Parameters

  - JSON body
    - `name` (string) (**required**) - The game's name used by the players to recognize it from the others (Connect Four actually put the [hostname](https://en.wikipedia.org/wiki/Hostname) in this parameter)
    - `version` (string) (**required**) - A Connect Four version i.e `1.0`

### `/games/{id}`

Provide ways to manipulate a single game.

##### Parameters

  - Query string
    - `{id}` (integer) (**required**) - A game ID

#### `GET`

Return a single game along a `200` or a `404` if the game wasn't found.

#### `PUT`

Update a game's data and return it with its newly updated attributes along a `200` or a `404` if the
game wasn't found.

##### Parameters

  - JSON body
    - `token` (string) (**required**) - The unique token required to perform critical operation on a game. If this token doesn't match the game's one, a `403` will be trown
    - `name` (string) - The game's name used by the players to recognize it from the others (Connect Four actually put the [hostname](https://en.wikipedia.org/wiki/Hostname) in this parameter)
    - `version` (string) - A Connect Four version i.e `1.0`
    - `status` (string) (one of `PLAYING`, `FINISHED`) - The new game status. If provided and identical to the current games's one, a `400` will be trown. If `PLAYING`, the `started_at` game attribute will be updated. If `FINISHED`, the `finished_at` game attribute will be updated and the `winner` parameter becomes required
    - `winner` (string) (one of `RED`, `YELLOW`) - The player who won the game. Required if the `status` parameter is provided and equals to `FINISHED`

#### `DELETE`

Delete a game along a `204` or a `404` if the game wasn't found.

##### Parameters

  - JSON body
    - `token` (string) (**required**) - The unique token required to perform critical operation on a game. If this token doesn't match the game's one, a `403` will be trown
