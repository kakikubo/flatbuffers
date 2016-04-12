#!/bin/sh

user=$1
asset_dir=${2:-`ls -1d ~/box/*_master_asset/ ~jenkins/box/*_master_asset/ ~kms.jenkins/box/kms_master_asset/ | head -1 2>/dev/null`}

jq -r ".\"$1\"" $asset_dir/manifests/chatwork-users.json | grep -v null
exit 0
