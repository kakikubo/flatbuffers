#!/bin/sh

port_base=7500
asset_list=~/box/kms_master_asset/manifests/dev.asset_list.json

for user_name in `jq -r '.[]' $asset_list`; do
  index=`jq -r ". | index(\"$user_name\")" $asset_list`
  port=$(($port_base + $index * 10))
  `dirname $0`/neo4j-multi-setup.sh $user_name $port || exit $?
done
exit 0
