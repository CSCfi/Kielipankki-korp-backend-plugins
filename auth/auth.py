#! /usr/bin/env python3

"""
auth.py

Flask WSGI application for the authorization server.

This application is based on the older auth.cgi script written mainly
by Jussi Piitulainen and Martin Matthiesen. Support for basic
authentication was removed.
"""


# The following has been copied from korp.py, but not all that may be necessary
# here, in particular if the script is run in a single thread.

# Skip monkey patching if run through gunicorn (which does the patching for us)
import os
if "gunicorn" not in os.environ.get("SERVER_SOFTWARE", ""):
    from gevent import monkey
    # Patching needs to be done as early as possible, before other imports
    monkey.patch_all(subprocess=False)

from gevent.pywsgi import WSGIServer
from gevent.threadpool import ThreadPool
from gevent.queue import Queue, Empty

# gunicorn patches everything, and gevent's subprocess module can't be
# used in native threads other than the main one, so we need to
# un-patch the subprocess module.
from importlib import reload
import subprocess
reload(subprocess)


import sys
import json
import MySQLdb
import logging

from flask import (Flask, request, Response, stream_with_context,
                   copy_current_request_context)
from flask_mysqldb import MySQL
from flask_cors import CORS

import config


app = Flask(__name__)
CORS(app)

# Configure database connection
app.config["MYSQL_HOST"] = config.DBHOST
app.config["MYSQL_USER"] = config.DBUSER
app.config["MYSQL_PASSWORD"] = config.DBPASSWORD
app.config["MYSQL_DB"] = config.DBNAME
app.config["MYSQL_PORT"] = config.DBPORT
app.config["MYSQL_USE_UNICODE"] = True
# app.config["MYSQL_CURSORCLASS"] = "DictCursor"
mysql = MySQL(app)


@app.route("/", methods=["GET", "POST"])
def auth():
    """Endpoint / returns permitted resources based on arguments.

    Return permitted resources based on username (remote_user),
    affiliation, and entitlement.
    """
    if request.is_json:
        args = request.get_json()
    else:
        args = request.values.to_dict()
    # Should the arguments and result be logged at the level info or debug?
    logging.info("Arguments: %s", args)
    result = _get_permitted_resources(
        *(args.get(key, "") for key in [
            "remote_user", "affiliation", "entitlement"]))
    logging.info("Result: %s", result)
    return Response(json.dumps(result), mimetype="application/json")


def _is_academic(affiliation, entitlement, clarin):
    """Return true if the user is academic based on the arguments."""
    aca_affiliation_values = [
        "member", "employee", "student", "faculty", "staff"]
    academic = (
        # Non-CLARIN username and affiliation is one of the above
        (not clarin
         and any(key in affiliation for key in aca_affiliation_values)
     ) or
        # CLARIN username and academic
        (clarin and
         "http://www.clarin.eu/entitlement/academic" in entitlement
     ) or
        # Academic status via LBR
        "urn:nbn:fi:lb-2016110710" in entitlement
    )
    return academic


def _get_permitted_resources(username, affiliation, entitlement):
    """Return permitted resources based on the arguments.

    username is the value of REMOTE_USER, affiliation is from
    Shibboleth and entitlement contains LBR REMS IDs (URNs) as a
    semicolon separated list.
    """
    logging.info("Username: %s", username)
    if not username:
        return dict(authenticated=False)

    cursor = mysql.connection.cursor()

    clarin = username.endswith("@clarin.eu")
    clarin_fi = username.endswith(".fi@clarin.eu")
    # Get the top-level-domain for checking ACA-Fi
    top_domain = username.rpartition(".")[-1]
    # Convert entitlement to an SQL-friendly form
    if entitlement:
        entitlement = tuple(filter(None, (entitlement + ";").split(";")))
    else:
        entitlement = tuple("")

    # Determine "academic status" based on supplied attributes
    academic = _is_academic(affiliation, entitlement, clarin)
    # Set topdomain = fi if the user is academic and a CLARIN user
    # with a .fi email.
    # The ACA status must have come from LBR in that case
    if academic and clarin_fi:
        top_domain = "fi"

    logging.debug("Is-Academic: %s", academic)
    logging.debug("Entitlement: %s", entitlement)

    # We can grant ACA status to people locally
    if not academic:
        cursor.execute("""
            select 1 from auth_academic
            where person = %s""", [username])
        if cursor.fetchone():
            academic = True

    # entitlement is a tuple of URNs that need mapping to Korp corpus IDs
    # Create as many parameters as entitlement has entries. The empty
    # list is "''"; eg 2 parameters yield ""%s", "%s""
    in_parameters=", ".join(map(lambda x: "'%s'", entitlement))
    if not in_parameters:
        in_parameters = "''"

    # The query with parameters filled in. This is easier to debug.
    sql="""
        select corpus from auth_license
        where %s = True and (license = 'ACA'
                             or (license = 'ACA-Fi' and '%s' = 'fi'))
        union distinct
        select corpus from auth_allow
        where person = '%s'
        union distinct
        select corpus from auth_lbr_map
        where lbr_id IN (%s); """ % (academic, top_domain, username,
                                     in_parameters)

    # Finally fill in entitlement values
    sql = sql % entitlement
    logging.debug("SQL: %s", sql)

    cursor.execute(sql)
    corpora = [corpus.upper() for corpus, in cursor]
    logging.info("Corpora: %s", corpora)

    return dict(authenticated=True,
                permitted_resources=dict(username=username,
                                         corpora=corpora))


if __name__ == "__main__":
    # Logging in this way may result in mixed lines if multiple instances of
    # the auth application are run simultaneously. However, it might suffice to
    # run a single instance at a time.
    logging.basicConfig(
        filename=config.LOG_FILE,
        format=("[auth.py %(levelname)s %(process)d @ %(asctime)s] "
                "%(message)s"),
        level=config.LOG_LEVEL)
    if len(sys.argv) == 2 and sys.argv[1] == "dev":
        # Run using Flask (use only for development)
        app.run(debug=True, threaded=True,
                host=config.WSGI_HOST, port=config.WSGI_PORT)
    else:
        # Run using gevent
        print("Serving using gevent")
        http = WSGIServer((config.WSGI_HOST, config.WSGI_PORT), app.wsgi_app)
        http.serve_forever()
