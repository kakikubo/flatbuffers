#!/bin/sh

export PATH=$PATH:/usr/local/bin
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = "$WATCHMAN_ROOT" ] && target=unknown
jenkins_url="http://127.0.0.1:8081/jenkins/job/102_KMS_UserAsset_Update/build"
jenkins_url_global="http://dev-kms.dev.gree.jp/jenkins/job/102_KMS_UserAsset_Update/build"
tool_dir=`dirname $0`/..

# logging
echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | jq '.'

# merge changed files log
head_file=/tmp/watchman-callback.$target.head.json
sonya_file=/tmp/watchman-callback.$target.sonya.log

touch $head_file || exit $?
echo "`cat $head_file` $json" | jq -s '.[0] + .[1]' > $head_file.tmp || exit $?
mv $head_file.tmp $head_file

# check box sync is completed
max=10
i=0
for i in `seq 1 $max`; do
  $tool_dir/script/box-sync-completed.sh && break
  sleep 1
done
if [ $i -ge $max ]; then
  cat $head_file | jq -r '.[] | (if .exists and .new then "A" elif .exists then "U" else "D" end) + " " + .["name"]' > $sonya_file
  echo "=== WAITING FOR BOX SYNC === " >> $sonya_file
  $tool_dir/script/sonya.sh "(yawn) watchman '$WATCHMAN_TRIGGER' of '$target' is waiting for Box Sync" $jenkins_url_global $sonya_file || exit $?
  exit 0
fi

# launch jenkins job
for file in `ls -t /tmp/watchman-callback.*.head.json`; do
  target=`basename $file | sed -e 's/^watchman-callback.//' | sed -e 's/.head.json$//'`
  echo "launch jenkins: $target"
  cat $file | jq '.'

  names=`cat $file | jq -r '.[] | (if .exists and .new then "A" elif .exists then "U" else "D" end) + " " + .["name"]' | tr '\n' '+'`
  param_file=/tmp/watchman-callback.$target.$$.json
  echo "{\"parameter\": [{\"name\": \"OPT_TARGET\", \"value\": \"$target\"}, {\"name\": \"OPT_FILES\", \"value\": \"$names\"}]}" > $param_file
  cat $param_file
  curl $jenkins_url -X POST --form json=@$param_file || exit $?

  rm -f $file || exit $?
done
exit 0
