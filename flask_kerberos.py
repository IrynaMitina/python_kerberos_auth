import logging
from functools import wraps
from socket import gethostname
from os import environ

import kerberos
from flask import Response, request, make_response

log = logging.getLogger(__name__)
_SPN = None


def init_kerberos(app, service='HTTP', hostname=gethostname()):
    global _SPN
    _SPN = "%s/%s" % (service, hostname)
    if 'KRB5_KTNAME' not in environ:
        log.warn("Kerberos: set KRB5_KTNAME to your keytab file")
    log.debug("getServerPrincipalDetails for spn={}".format(_SPN))
    principal = kerberos.getServerPrincipalDetails(service, hostname)


def requires_authentication(view):
    @wraps(view)
    def decorated(*args, **kwargs):
        krb_context = None
        try:
            # client token
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                raise kerberos.KrbError("no auth header in client request")
            if not auth_header.startswith("Negotiate"):
                raise kerberos.KrbError("client auth requires a negotiate request")
            token = ''.join(auth_header.split()[1:])

            # obtain session key from token
            log.debug("authGSSServerInit")
            status, krb_context = kerberos.authGSSServerInit("HTTP")
            if status != 1:  # not complete
                raise kerberos.KrbError("authGSSServerInit failed with status={}".format(status))
            log.debug("authGSSServerStep")
            status = kerberos.authGSSServerStep(krb_context, token)
            if status != 1:
                raise kerberos.KrbError("authGSSServerStep failed with status={}".format(status))

            # get user id
            log.debug("authGSSServerUserName")
            user = kerberos.authGSSServerUserName(krb_context)
            request.current_user = user
            request.session_context = krb_context
            log.debug("kerberos user={}".format(user))

            # respond with authenticator (mutual auth)
            response = make_response(view(user, *args, **kwargs))
            log.debug("authGSSServerResponse")
            kerberos_token = kerberos.authGSSServerResponse(krb_context)
            if kerberos_token is not None:
                response.headers['WWW-Authenticate'] = "Negotiate " + kerberos_token

        except kerberos.KrbError as e:
            logging.exception(e)
            request.current_user = None
            request.session_context = None
            return Response('Unauthorized', 401, {'WWW-Authenticate': 'Negotiate'})
        finally:
            if krb_context:
                status = kerberos.authGSSServerClean(krb_context)
                if status != 1:
                    log.warning("authGSSServerClean failed with status={}".format(status))
        return response
    return decorated
