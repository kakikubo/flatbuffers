#!/bin/sh

export PATH=$PATH:/usr/local/bin
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = "$WATCHMAN_ROOT" ] && target=unknown
jenkins_url="http://127.0.0.1:8081/job/102_KMS_UserAsset_Update/build"

# logging
echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | jq '.'

# launch jenkins job
json_file=/tmp/watchman-callback.$$.json
names=`echo $json | jq -r '.[]["name"]'`
echo "{\"parameter\": [{\"name\": \"OPT_TARGET\", \"value\": \"$target\"}, {\"name\": \"OPT_FILES\", \"value\": \"$names\"}]}" > $json_file
curl $jenkins_url -X POST --form json=@$json_file
exit $?
