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

function get_names() {
  echo `cat $1 | jq -r '.[] | (if .exists and .new then "A" elif .exists then "U" else "D" end) + " " + .["name"]' | tr '\n' '+'`
}

# merge changed files log
head_file=/tmp/watchman-callback.$target.head.json
current_file=/tmp/watchman-callback.$target.current.json
sonya_file=/tmp/watchman-callback.$target.sonya.log

touch $head_file || exit $?
echo "`cat $head_file` $json" | jq -s '.[0] + .[1]' > $current_file || exit $?

# check box sync is completed
if ! $tool_dir/script/box-sync-completed.sh; then
  mv $current_file $head_file
  get_names $current_file > $sonya_file
  $tool_dir/script/sonya.sh "(yawn) watchman '$WATCHMAN_TRIGGER' is waiting for Box Sync" $kms_dev_url $sonya_file || exit $?
  exit 0
fi

# launch jenkins job
for file in `ls -t /tmp/watchman-callback.*.head.json`; do
  target=`basename $file | sed -e 's/^watchman-callback.//' | sed -e 's/.head.json$//'`
  names=`get_names $file`
  param_file=/tmp/watchman-callback.$target.$$.json
  echo "{\"parameter\": [{\"name\": \"OPT_TARGET\", \"value\": \"$target\"}, {\"name\": \"OPT_FILES\", \"value\": \"$names\"}]}" > $param_file
  cat $param_file
  curl $jenkins_url -X POST --form json=@$param_file || exit $?
  rm -f $file || exit $?
done
exit 0
