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
It can be a `200` or `201` with JSON output. Read the resource's doc.

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

They should not happen. If so, please report an issue [here](https://github.com/EpocDotFr/connectfour-master-server/issues).

Example:

```json
{
    "message": "Error creating this thing: (sqlite3.IntegrityError) UNIQUE constraint failed: thing.thingy"
}
```

## Objects

Here are all the object types that the API can return.

### Game

```json
{
  "country": "FR",
  "created_at": "2017-03-11T12:47:01.303415+00:00",
  "finished_at": "2017-03-11T13:59:35.082576+00:00",
  "id": 1,
  "token": "b2467592ba4148e1bfa4374384c38cc7",
  "ip": "6.6.6.6",
  "name": "PC-Epoc",
  "started_at": "2017-03-11T12:51:01.302415+00:00",
  "status": "FINISHED",
  "version": "1.0",
  "winner": "RED"
}
```

  - `country` (string) - The [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) country code of the `ip` who created the game. Can be `null` if cannot be determined
  - `created_at` (string) - [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) creation date of the game
  - `finished_at` (string) - [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) finish date of the game. Can be `null`
  - `id` (integer) - Unique ID of the game
  - `token` (string) - Unique token required to perform write operation on a game. **Only issued after successfully creating a game** (see below)
  - `ip` (string) - IP of the games's creator (one IP cannot create more than one game)
  - `name` (string) - The game's name used by the players to recognize it from the others (Connect Four actually put the [hostname](https://en.wikipedia.org/wiki/Hostname) in this parameter)
  - `started_at` (string) - [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) starting date of the game. Can be `null`
  - `status` (string) - Current status of the game. Can be one of `WAITING`, `PLAYING`, `FINISHED`. If `FINISHED`, `winner` is not `null`
  - `version` (string) - A Connect Four version i.e `1.0`
  - `winner` (string) - The player who won the game. `null` if `status` is different from `FINISHED`. Can be one of `RED`, `YELLOW` otherwise

> A game may be deleted by the server automatically at any time if the game's latest ping is older than now minus 5 minutes
> (by default) and if it has a status different from `FINISHED`.

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
    - `country` (string) - A country code, as defined in the [ISO 3166-1 alpha-2](https://en.wikipedia.org/wiki/ISO_3166-1_alpha-2) standard
    - `name` (string) - A full or partial game name

#### `POST`

Create a new game and return it along a `201`. A unique token is returned along the game's data if created
successfully: this token will be required for any future write operation on this game. **This token
will only be issued once**, so be sure to put it somewhere in a variable.

##### Parameters

  - JSON body
    - `name` (string) (**required**) - The game's name used by the players to recognize it from the others (Connect Four actually put the [hostname](https://en.wikipedia.org/wiki/Hostname) in this parameter)
    - `version` (string) (**required**) - A Connect Four version i.e `1.0`

### `/games/{id}`

Provide ways to manipulate a single game.

##### Parameters

  - URI parameters
    - `{id}` (integer) (**required**) - A game ID

#### `GET`

Return a single game along a `200` or a `404` if the game wasn't found.

#### `PUT`

Update a game's data and return it with its freshly updated attributes along a `200` or a `404` if the
game wasn't found. If trying to update a game who have the `FINISHED` status, a `403` will be thrown.

The game's `last_ping_at` private attribute is updated each time this endpoint is called. This
attribute is only used by the Cron task responsible to clean old and inactive games. Thus, it is
possible to call this endpoint without any argument (except the required ones) only to update this
attribute.

##### Parameters

  - JSON body
    - `token` (string) (**required**) - The unique token required to perform write operation on a game. If this token doesn't match the game's one, a `403` will be thrown
    - `name` (string) - The game's name used by the players to recognize it from the others (Connect Four actually put the [hostname](https://en.wikipedia.org/wiki/Hostname) in this parameter)
    - `version` (string) - A Connect Four version i.e `1.0`
    - `status` (string) (one of `PLAYING`, `FINISHED`) - The new game status. If provided and identical to the current games's one, a `400` will be thrown. If `PLAYING`, the `started_at` game attribute will be updated. If `FINISHED`, the `finished_at` game attribute will be updated and the `winner` parameter becomes required
    - `winner` (string) (one of `RED`, `YELLOW`) - The player who won the game. Required if the `status` parameter is provided and equal to `FINISHED`

#### `DELETE`

Delete a game and return a `204` with no body or a `404` if the game wasn't found. If trying to delete
a game who have the `FINISHED` status, a `403` will be thrown.

##### Parameters

  - JSON body
    - `token` (string) (**required**) - The unique token required to perform write operation on a game. If this token doesn't match the game's one, a `403` will be thrown
