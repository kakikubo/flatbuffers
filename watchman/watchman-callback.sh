#!/bin/sh

export PATH=$PATH:/usr/local/bin
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = "$WATCHMAN_ROOT" ] && target=unknown
jenkins_url="http://127.0.0.1:8081/job/102_KMS_UserAsset_Update/build"
kms_dev_url=http://kms-dev.dev.gree.jp/
tool_dir=`dirname $0`/..

# logging
echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | jq '.'

# merge changed files log
head_file=/tmp/watchman-callback.head.json
current_file=/tmp/watchman-callback.current.json
param_file=/tmp/watchman-callback.$$.json
sonya_file=/tmp/watchman-callback.sonya.$$.log

touch $head_file || exit $?
echo "`cat $head_file` $json" | jq -s '.[0] + .[1]' > $current_file || exit $?
names=`cat $current_file | jq -r '.[] | (if .exists and .new then "A" elif .exists then "U" else "D" end) + " " + .["name"]' | tr '\n' '+'`

# check box sync is completed
if ! $tool_dir/script/box-sync-completed.sh; then
  mv $current_file $head_file
  echo $names > $sonya_file
  $tool_dir/script/sonya.sh "(yawn) watchman '$WATCHMAN_TRIGGER' is waiting for Box Sync" $kms_dev_url $sonya_file || exit $?
  exit 0
fi
rm -f $head_file || exit $?

# launch jenkins job
echo "{\"parameter\": [{\"name\": \"OPT_TARGET\", \"value\": \"$target\"}, {\"name\": \"OPT_FILES\", \"value\": \"$names\"}]}" > $param_file
cat $param_file
curl $jenkins_url -X POST --form json=@$param_file
exit $?
