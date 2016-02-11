#!/bin/sh

user=$1
asset_dir=$2
[ -d "$asset_dir" ] || asset_dir=~/box/kms_master_asset/
[ -d "$asset_dir" ] || asset_dir=~jenkins/box/kms_master_asset/
[ -d "$asset_dir" ] || asset_dir=~kms.jenkins/box/kms_master_asset/

jq -r ".\"$1\"" $asset_dir/manifests/chatwork-users.json | grep -v null
exit $?
