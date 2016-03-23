#!/bin/sh

asset_list=~/box/kms_master_asset/manifests/dev.asset_list.json

exit_code=0
for user_name in `jq -r '.[]' $asset_list`; do
  echo "$user_name $*..."
  NEO4J_HOME=${NEO4J_MULTI_ROOT:-~/neo4j}/$user_name `dirname $0`/neo4j $*
  [ $? -eq 0 ] || exit_code=$?
done
exit $exit_code

