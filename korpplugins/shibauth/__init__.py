
"""
korpplugins.shibauth

A Korp callback plugin to support authorization with information
obtained from Shibboleth authentication in /authenticate.

Ported to a Korp backend plugin from the modifications made to Korp
for the Language Bank of Finland, originally by Jussi Piitulainen.
"""


import korppluginlib


class ShibbolethAuthorizer(korppluginlib.KorpCallbackPlugin):

    """A Korp callback plugin for authentication handling Shibboleth info"""

    def filter_auth_postdata(self, postdata, request):
        """If REMOTE_USER is set, return postdata with Shibboleth info.

        If REMOTE_USER is set, return postdata with remote_user,
        affiliation and entitlement set from the corresponding
        environment variables set by Shibboleth (or from the
        corresponding headers set by the reverse proxy); otherwise
        return postdata intact.
        """

        def get_value(key):
            """Get the value of env variable key or the corresponding header.

            If the environment variable `key` does not exist or is
            empty, try the corresponding HTTP headers X-Key and Key,
            where Key is title-cased and with the possible "HTTP_"
            prefix removed.
            """
            value = request.environ.get(key)
            if not value:
                # Try to get a value from HTTP headers
                if key.startswith("HTTP_"):
                    key = key[5:]
                key = key.replace("_", "-").title()
                value = (request.headers.get("X-" + key)
                         or request.headers.get(key)
                         or "")
            return value

        remote_user = get_value("REMOTE_USER")
        if remote_user:
            # In which order should we check the affiliation variables?
            affiliation = (get_value("HTTP_UNSCOPED_AFFILIATION") or
                           get_value("HTTP_AFFILIATION"))
            entitlement = get_value("HTTP_ENTITLEMENT")
            postdata = {
                "remote_user": remote_user,
                "affiliation": affiliation.lower(),
                "entitlement": entitlement,
            }
        return postdata
