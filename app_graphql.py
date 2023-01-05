import logging

from flask import Flask
from flask_graphql import GraphQLView

from graphene_kerberos import init_kerberos, kerberos_auth_middleware


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


####################################################### users & permissions
class Forbidden(Exception):
    def __init__(self, msg='Forbidden', *args, **kwargs):
        super().__init__(msg, *args, **kwargs)


PERM_READ = 1
PERM_MODIFY = 2

USERS_PERMISSIONS = {
    'iryna@HOME.ORG.AU': PERM_MODIFY | PERM_READ,
    'tom@HOME.ORG.AU': PERM_READ,
    'jerry@HOME.ORG.AU': 0  # no permissions
}

####################################################### graphene
from graphene import (Schema, ObjectType, List, Int, String, Field, Boolean,
                      Mutation)
from graphene_kerberos import auth_required


class Query(ObjectType):
    all_strings = List(String)
    hello = String()

    @staticmethod
    @auth_required
    def resolve_all_strings(parent, info, **kwargs):
        logger.debug("resolve_all_strings: current_user={}".format(info.context.current_user))
        if not (PERM_READ & USERS_PERMISSIONS[info.context.current_user]):
            raise Forbidden
        return ['hello', 'me', 'from', 'myself']

    @staticmethod
    def resolve_hello(parent, info, **kwargs):
        return "hello!"


class DeleteItem(Mutation):
    class Arguments:
        iid = Int(required=True)

    deleted = Boolean()

    @staticmethod
    @auth_required
    def mutate(root, info, iid):
        logger.debug("DeleteItem: iid={}, current_user={}".format(iid, info.context.current_user))
        if not (PERM_MODIFY & USERS_PERMISSIONS[info.context.current_user]):
            raise Forbidden
        return DeleteItem(deleted=True)


class Mutate(ObjectType):
    delete_item = DeleteItem.Field()


schema = Schema(query=Query, mutation=Mutate, auto_camelcase=False)

####################################################### flask
app = Flask(__name__)
app.add_url_rule(
    "/graphql", view_func=GraphQLView.as_view(
        "graphql", schema=schema, graphiql=False, middleware=[kerberos_auth_middleware])
)

if __name__ == "__main__":
    init_kerberos(app, hostname='kerberos-graphql-service.home.org.au')
    app.run(host='0.0.0.0', port=5500)
