#!/bin/sh

port_base=7500
asset_list=${KMS_ASSET_LIST:-`ls -1d ~/box/*_master_asset/manifests/dev.asset_list.json | head -1 2>/dev/null`}

for user_name in `jq -r '.[]' $asset_list`; do
  echo "$user_name..."
  index=`jq -r ". | index(\"$user_name\")" $asset_list`
  port=$(($port_base + $index * 10))
  `dirname $0`/neo4j-multi-setup.sh $user_name $port || exit $?
done
exit 0
