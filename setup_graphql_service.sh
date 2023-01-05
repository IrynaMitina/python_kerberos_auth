#add principal and save its key in keytab
kadmin -p root/admin -w padmin -q "addprinc -randkey HTTP/kerberos-graphql-service.home.org.au"
kadmin -p root/admin -w padmin -q "ktadd HTTP/kerberos-graphql-service.home.org.au"

#launch app
export KRB5_KTNAME=/etc/krb5.keytab
python3 /app_graphql.py