#!/bin/sh -xe

cd `dirname $0`

proxy=login-kms.gree-dev.net
remote_host=hockeyproxy
dir=/var/www/cgi-bin
targets="box-webhook.sh github-webhook.sh hockeyapp-webhook.sh"

asset_dir=
[ -d "$asset_dir" ] || asset_dir=~/box/kms_master_asset/
[ -d "$asset_dir" ] || asset_dir=~jenkins/box/kms_master_asset/
[ -d "$asset_dir" ] || asset_dir=~kms.jenkins/box/kms_master_asset/
chatwork_users=$asset_dir/manifests/chatwork-users.json
if [ -f $chatwork_users ]; then
  cp -p $chatwork_users chatwork-users.json
  chmod a+rw chatwork-users.json
  targets="$targets chatwork-users.json"
fi

rsync -av -e "ssh $proxy gaws ssh" $targets $remote_host:$dir/
exit $?
