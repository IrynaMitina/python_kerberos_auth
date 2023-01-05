#!/bin/bash

echo "127.0.0.1 kerberos.home.org.au" >> /etc/hosts

mkdir -p /var/log/kerberos

# /var/kerberos/krb5kdc/principal - database
/usr/sbin/kdb5_util -P pkey create -s
kadmin.local -q "addprinc -pw padmin root/admin"
kadmin.local -q "addprinc -pw piryna iryna"
kadmin.local -q "addprinc -pw ptom tom"
kadmin.local -q "addprinc -pw pjerry jerry"
kadmin.local -q "addprinc -randkey HTTP/kerberos.home.org.au"
kadmin.local -q "ktadd -k /etc/http.keytab HTTP/kerberos.home.org.au"

/usr/sbin/krb5kdc &
/usr/sbin/kadmind &

sleep infinity
