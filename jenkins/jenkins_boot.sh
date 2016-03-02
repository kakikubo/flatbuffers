#!/bin/sh -x
PATH="/usr/local/bin":$PATH ; export PATH
PP=`cat /var/tmp/pass`
logger "launch jenkins daemon from launchctl "
expect -c "
set timeout 1
spawn ssh-add $HOME/.ssh/id_rsa_ghe
expect {
  \"Enter passphrase for\" {
    send \"${PP}\"
  }
}
exit 0
"
logger "exec jenkins"
jenkins --prefix=/jenkins --httpPort=8080
#jenkins --prefix=/jenkins --httpPort=8081 &
#exit $?
