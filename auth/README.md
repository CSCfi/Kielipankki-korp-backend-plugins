
# Korp authorization server of the Language Bank of Finland

This directory contains an authorization server for the Korp backend
of the [Language Bank of Finland
(Kielipankki)](https://www.kielipankki.fi/language-bank).

The authorization server is a Python 3 WSGI application. It uses
parameters from Shibboleth authentication to return information on the
resources (corpora) that the authenticated user is allowed to use.


## Requirements

To use the authorization server, you need the following:

* [Python 3.6+](http://python.org/)
* [MariaDB](https://mariadb.org/) or [MySQL](http://www.mysql.com/)


## Setting up the Python environment and requirements

Optionally you may set up a virtual Python environment:

    $ python3 -m venv venv
    $ source venv/bin/activate

Install the required Python modules using `pip` with the included
[`requirements.txt`](requirements.txt).

    $ pip3 install -r requirements.txt


## Configuring the authorization server

The authorization server is configured by editing `config.py`, for
which a template is provided in
[`config.py.template`](config.py.template).

The following variables need to be set:

* `WSGI_HOST` and `WSGI_PORT`: Host and port for the WSGI server.
* `DBHOST`, `DBPORT` and `DBNAME`: The host, port and name of the
  MariaDB or MySQL database where authorization information is stored.
* `DBUSER` and `DBPASSWORD`: Username and password for accessing the
  database.
* `LOG_FILE`: The name of the file into which to write log information.
* `LOG_LEVEL`: The log level at which to write entries to the log file
  (`logging.INFO`, `logging.DEBUG` or `logging.WARNING`).


## Running the authorization server

To run the authorization server, simply run `auth.py`:

    python3 auth.py

The authorization server should then be reachable in your web browser
on the port you configured in `config.py`, for example
`http://localhost:1235`.

During development or while testing your configuration, use the flag
`dev` for automatic reloading.

    python3 auth.py dev

For deployment, [Gunicorn](http://gunicorn.org/) works well.

    gunicorn --worker-class gevent --bind 0.0.0.0:1235 --workers 1 --max-requests 250 --limit-request-line 0 auth:app


## API

The authorization server has a single endpoint `/` that recognizes the
following parameters:

* `remote_user`: The username from `REMOTE_USER`.
* `affiliation`: Affilitation information from Shibboleth.
* `entitlement`: A list of LBR IDs (URNs) for resources permitted to
  the user as a semicolon-separated list.
* `format` (optional): If the value is `short`, use a shorter output
  format (see below).
* `debug` (optional): If the value is `1`, `true` or `yes`, set log
  level to `logging.DEBUG`, which outputs some debug information to
  the log file.

For example:
`http://localhost:1235/?remote_user=user@example.com&affiliation=member&entitlement=urn:nbn:fi:lb-20140711234@LBR;urn:nbn:fi:lb-20140711235@LBR`

The JSON output contains the following items:

* `authenticated` (Boolean): Whether the user is authenticated or not.
* `permitted_resources`:
  * `username` (string): Username from parameter `remote_user`.
  * `corpora`:
    * Default format: A mapping object whose keys are the upper-case
      Korp corpus ids that the user is allowed to access, each with
      the value `{"read": true}`.
    * Format with parameter `format=short`: A list of upper-case Korp
      corpus ids that the user is allowed to access.

For example:

```json
{
  "authenticated": true,
  "permitted_resources": {
    "username": "user@example.com",
    "corpora": {
      "CORP1": {"read": true},
      "CORP2": {"read": true}
    }
  }
}
```

(*TODO*: Write an OpenAPI specification for the API.)
