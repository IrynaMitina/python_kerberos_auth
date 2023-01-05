import sys
import logging 

from flask import Flask, request
from flask_kerberos import requires_authentication, init_kerberos
import kerberos



# logging
logger = logging.getLogger()  # root logger
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
fh = logging.FileHandler('/app.log')
fh.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

app = Flask(__name__)


@app.route("/protected")
@requires_authentication
def protected_view(user):
    logger.debug("***** protected_view: user={}".format(request.current_user))
    return 'protected info'


@app.route('/')
def hello_world():
    return 'Hello, my World!'


if __name__ == "__main__":
    init_kerberos(app, hostname='kerberos-flask-service.home.org.au')
    app.run(host='0.0.0.0', port=5555)
