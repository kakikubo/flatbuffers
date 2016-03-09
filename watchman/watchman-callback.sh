#!/bin/sh

export PATH=$PATH:/usr/local/bin
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = "$WATCHMAN_ROOT" ] && target=unknown

tool_dir=`dirname $0`/..
sonya_file=/tmp/watchman-callback.$target.sonya.log
chat_id=45378088  # KMS Box Sync タイムライン

#jenkins_url="http://127.0.0.1:8080/jenkins/job/102_KMS_UserAsset_Update/build"
#jenkins_url="http://dev-kms.dev.gree.jp/jenkins/job/102_KMS_UserAsset_Update/build"
jenkins_url="http://g-pc-00363221.intra.gree-office.net:8080/jenkins/job/102_KMS_UserAsset_Update/build"
asset_dir="kms_${target}_asset/`echo $WATCHMAN_TRIGGER | tr '-' '/'`"

# logging
echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | jq '.'
echo $json | jq -r '.[] | (if .exists and .new then "A" elif .exists then "U" else "D" end) + " " + .["name"]' > $sonya_file
$tool_dir/script/sonya2.sh $chat_id "[info][title](yawn) Box Sync $asset_dir is updated[/title]$jenkins_url[code]`cat $sonya_file`[/code][/info]" || exit $?

exit 0
