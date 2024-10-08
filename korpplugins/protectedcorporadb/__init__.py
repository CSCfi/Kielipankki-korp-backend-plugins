
"""
korpplugins.protectedcorporadb

Retrieve a list of protected corpora from a MySQL database.
"""


import MySQLdb

import korppluginlib

# See config.py.template for further documentation of the configuration
# variables
pluginconf = korppluginlib.get_plugin_config(
    # All MySQL connection parameters as a dict; if non-empty, overrides the
    # individual DBCONN_* values
    DBCONN_PARAMS = {},
    # MySQL connection parameters as individual values
    DBCONN_HOST = "localhost",
    DBCONN_PORT = 3306,
    # DBCONN_UNIX_SOCKET should be commented-out unless using a non-default
    # socket for connecting
    # DBCONN_UNIX_SOCKET = ""
    DBCONN_DB = "korp_auth",
    DBCONN_USER = "korp",
    DBCONN_PASSWD = "",
    DBCONN_USE_UNICODE = True,
    DBCONN_CHARSET = "utf8mb4",
    # The name of the table containing licence information, to be filled in
    # LIST_PROTECTED_CORPORA_SQL
    LICENCE_TABLE = "auth_license",
    # SQL statement to list protected corpora
    LIST_PROTECTED_CORPORA_SQL = """
        SELECT corpus FROM {LICENCE_TABLE}
        WHERE NOT license LIKE 'PUB%'
    """,
    # Whether to keep the database connection persistent or close after each
    # call of filter_protected_corpora
    PERSISTENT_DB_CONNECTION = True,
)


class ProtectedCorporaDatabase(korppluginlib.KorpCallbackPlugin):

    """Callback plugin class for retrieving protected corpora from database"""

    def __init__(self):
        """Initialize but do not connect to the database yet."""
        super().__init__()
        self._connection = None
        # Fill in values in LIST_PROTECTED_CORPORA_SQL from other values in
        # pluginconf
        self._list_protected_corpora_sql = (
            pluginconf.LIST_PROTECTED_CORPORA_SQL.format(
                **pluginconf.__dict__))
        # Non-empty DBCONN_PARAMS overrides individual DBCONN_* values
        self._conn_params = (
            pluginconf.DBCONN_PARAMS
            or dict((key.lower().split("_", 1)[1], val)
                    for key, val in pluginconf.__dict__.items()
                    if (key.startswith("DBCONN_")
                        and key != "DBCONN_PARAMS")))

    def __del__(self):
        """Close connection when deleting the object."""
        self._disconnect()

    def filter_protected_corpora(self, protected_corpora, request):
        """Append to protected_corpora corpora in authorization database."""
        connection_errors = (
            AttributeError,
            MySQLdb.MySQLError,
            MySQLdb.InterfaceError,
            MySQLdb.DatabaseError,
        )

        def db_fetch():
            with self._connection.cursor() as cursor:
                cursor.execute(self._list_protected_corpora_sql)
                return [corpus for corpus, in cursor]

        if self._connect():
            try:
                protected_corpora.extend(db_fetch())
            except connection_errors:
                # retry in case connection is in bad state
                # if we still can't connect, cause exception & handle it in
                # the caller, which can try to use its cache
                self._connect(force_reconnect=True)
                try:
                    protected_corpora.extend(db_fetch())
                except connection_errors:
                    raise ConnectionError

        # If the database connection is not persistent, close it
        if not pluginconf.PERSISTENT_DB_CONNECTION:
            self._disconnect()

        return protected_corpora

    def _disconnect(self):
        """Disconnect from authorization database and set self._connection to None."""
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def _connect(self, force_reconnect = False):
        """Connect to authorization database if not already connected.

        Connect to the authorization database with parameters
        specified in the DBCONN_* configuration variables. Set
        self._connection to the connection and return it. If
        connecting fails, set it to None and return None. If
        force_reconnect is True, make a connection in any case.
        """
        if force_reconnect:
            self._disconnect()
        if not self._connection:
            try:
                self._connection = MySQLdb.connect(**self._conn_params)
            except (MySQLdb.MySQLError, MySQLdb.InterfaceError,
                    MySQLdb.DatabaseError) as e:
                print("korpplugins.protectedcorporadb: Error connecting"
                      " to database:", e)
                self._connection = None
                raise ConnectionError
        return self._connection
