import logging
from functools import wraps
from socket import gethostname
from os import environ

import kerberos
from graphql.execution.base import ResolveInfo

log = logging.getLogger(__name__)
_SPN = None


def context(f):
    def decorator(func):
        def wrapper(*args, **kwargs):
            info = next(arg for arg in args if isinstance(arg, ResolveInfo))
            return func(info.context, *args, **kwargs)
        return wrapper
    return decorator


def auth_required(f):
    @wraps(f)
    @context(f)
    def wrapper(context, *args, **kwargs):
        if not context.current_user:
            raise Exception("UnAuthorized")
        return f(*args, **kwargs)
    return wrapper


def init_kerberos(app, service='HTTP', hostname=gethostname()):
    global _SPN
    _SPN = "%s/%s" % (service, hostname)
    if 'KRB5_KTNAME' not in environ:
        log.warn("Kerberos: set KRB5_KTNAME to your keytab file")
    log.debug("getServerPrincipalDetails for spn={}".format(_SPN))
    principal = kerberos.getServerPrincipalDetails(service, hostname)


def kerberos_auth_middleware(next, root, info, **kwargs):
    request_context = info.context
    krb_context = None
    try:
        # client token
        auth_header = request_context.headers.get("Authorization")
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
        request_context.current_user = user
        log.debug("kerberos user={}".format(user))

        # no mutual auth
    except kerberos.KrbError as e:
        logging.exception(e)
        request_context.current_user = None
    finally:
        if krb_context:
            status = kerberos.authGSSServerClean(krb_context)
            if status != 1:
                log.warning("authGSSServerClean failed with status={}".format(status))
    
    return next(root, info, **kwargs)

