# Hands on kerberos: flask app, graphql app
Kerberos authentication is implemented for flask application and for graphql application.
KDC, service provider and client run in docker containers.

to use container name as dns, create network for all components:
```
docker network create kerbnet
```

## launch KDC server
```
docker build --tag=mydockerid/kerberos -f DockerfileKDC .
docker run -d --rm --network kerbnet --name kerberos.home.org.au -p 749:749 -p 88:88 mydockerid/kerberos
```
and verify by obtaining TGT from within container
```
docker exec -it kerberos.home.org.au bash
klist
kinit iryna
klist
```

## launch flask service
```bash
docker build --tag=mydockerid/kerberos-flask-service -f DockerfileFlask .
docker run -it --rm --network kerbnet --name kerberos-flask-service.home.org.au -p 5555:5555 mydockerid/kerberos-flask-service
```

and verify service is working by
```
curl http://localhost:5555/
```
and verify presense of principal `HTTP/kerberos-flask-service.home.org.au@HOME.ORG.AU` and keytab for the service by
```
docker exec -it kerberos-flask-service.home.org.au bash
kadmin -p root/admin -w padmin -q "listprincs"
klist -kt /etc/krb5.keytab
```

## launch graphql service
```
docker build --tag=mydockerid/kerberos-graphql-service -f DockerfileGraphql .
docker run -it --rm --network kerbnet --name kerberos-graphql-service.home.org.au -p 5500:5500 mydockerid/kerberos-graphql-service
```

## launch client
```
docker build --tag=mydockerid/kerberos-client -f DockerfileClient .
docker run -it --rm --network kerbnet --name kerberos-client.home.org.au mydockerid/kerberos-client bash
```

## client: verify kerberos auth with flask service
```
python3 -c 'import requests; import requests_kerberos; r = requests.get("http://kerberos-flask-service.home.org.au:5555/protected", auth=requests_kerberos.HTTPKerberosAuth()); print(r)'
```
it should fail, 
then authenticate (TGT) and repeat
```
kinit iryna
python3 -c 'import requests; import requests_kerberos; r = requests.get("http://kerberos-flask-service.home.org.au:5555/protected", auth=requests_kerberos.HTTPKerberosAuth()); print(r); print(r.text)'
```
should be ok now;
for invalidating TGT use `kdestroy` command;

## client: verify kerberos auth with graphql service
```python
import requests; import requests_kerberos
url = "http://kerberos-graphql-service.home.org.au:5500/graphql"
# 1. requesting 'hello' does not require authentication
r = requests.post(url, json={'query': "query { hello }"})
print(r.status_code, r.json())

# 2. requesting 'all_strings' requires authentication
r = requests.post(url, json={'query': "query { all_strings }"})
print(r.status_code, r.json())  # server returns UnAuthorized error
r = requests.post(url, json={'query': "query { all_strings }"},  auth=requests_kerberos.HTTPKerberosAuth())
```
last request raises 'No Kerberos credentials available', so we authenticate to get TGT
```
kinit iryna
```
and then repeat request - should work now;


to check permissions, first invalidate kerberos cache (TGT):
```
kdestroy
```
login as user jerry (no permissions for the graphql app)
```
kinit jerry
```
then try to query and mutation 
```python
import requests; import requests_kerberos
url = "http://kerberos-graphql-service.home.org.au:5500/graphql"
# 1. query 'all_strings' requires read permissions
r = requests.post(url, json={'query': "query { all_strings }"},  auth=requests_kerberos.HTTPKerberosAuth())
print(r.status_code, r.json())
# 2. mutation requires write permissions
query = """
mutation {
    delete_item (iid: 4) {
        deleted
    }
}
"""
r = requests.post(url, json={'query': query},  auth=requests_kerberos.HTTPKerberosAuth())
print(r.status_code, r.json()) 
```
both should return Forbidden error;

then destroy the cache, login as 'tom' and repeat same queries
('tom' can read, but cannot write);
then again destroy the cache, login as 'iryna' and repeat same queries
('iryna' can do both read and write);


## auth debugging
add `-e "KRB5_TRACE=/dev/stdout"` to `docker run ..` for client and service provider, to get detailed auth logging output

## notes on non-dns-based SPN
This kerberos-auth playground implementation uses DNS-based SPN for service,
but actually SPN can be arbitrary.
For arbitrary SPN: 
no service changes are required, 
client should provide SPN as argument to HTTPKerberosAuth instead of parsing it 
from url.
