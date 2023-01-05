#add principal and save its key in keytab
kadmin -p root/admin -w padmin -q "addprinc -randkey HTTP/kerberos-flask-service.home.org.au"
kadmin -p root/admin -w padmin -q "ktadd HTTP/kerberos-flask-service.home.org.au"

#launch app
export KRB5_KTNAME=/etc/krb5.keytab
python3 /app_flask.py