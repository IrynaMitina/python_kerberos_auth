import logging

from requests.auth import AuthBase
import kerberos


# TODO: gss flags (mutual auth), comments about what stages do
# TODO: urlparse for host
log = logging.getLogger(__name__)
SPN_TMPL = "HTTP@{host}"



class HTTPKerberosAuth(AuthBase):
    def __call__(self, request):
        host = request.url.split(":")[1].strip("/")
        spn = SPN_TMPL.format(host=host)
        krb_context = None
        try:
            # obtain session key for service using TGT
            log.debug("authGSSClientInit for spn={}".format(spn))
            status, krb_context = kerberos.authGSSClientInit(spn)
            if status != 1:  # not complete
                raise kerberos.KrbError("client init failed for spn={}".format(spn))
            log.debug("authGSSClientStep")
            kerberos.authGSSClientStep(krb_context, "")
            log.debug("authGSSClientResponse")
            kerberos_token = kerberos.authGSSClientResponse(krb_context)
            request.headers["Authorization"] = "Negotiate " + kerberos_token
            return request
        finally:
            if krb_context:
                status = kerberos.authGSSClientClean(krb_context)
                if status != 1:
                    log.warning("authGSSClientClean failed with status={}".format(status))
