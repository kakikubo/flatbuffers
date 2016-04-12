#!/bin/sh

asset_list=${KMS_ASSET_LIST:-`ls -1d ~/box/*_master_asset/manifests/dev.asset_list.json | head -1 2>/dev/null`}
query=`dirname $0`/../query.py

exit_code=0
for user_name in `jq -r '.[]' $asset_list`; do
  echo "$user_name $*..."
  index=`jq -r ". | index(\"$user_name\")" $asset_list`
  port=$((7500+$index*10))
  neo4j_url="http://neo4j:fflkms001@localhost:${port}/db/data/"
  $query --neo4j-url $neo4j_url $*
  [ $? -eq 0 ] || exit_code=$?
done
exit $exit_code
