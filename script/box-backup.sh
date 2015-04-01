#!/bin/sh

source `dirname $0`/box-config.sh
top_dir="`dirname $0`/../"
backup_dir="kms_asset_backup.`date +'%Y%m%d_%H%M%S'`"
filename=$backup_dir.tar.bz2

parent_id=3321638512  # kms_backup/asset
access_token=`git config box.accesstoken` || exit $?

cd $top_dir
target_dir=`pwd`

cd # go to home dir
echo "$target_dir -> $backup_dir"
git clone --mirror $target_dir $backup_dir > /dev/null || exit $?
tar jcf $filename $backup_dir || exit $?

echo "upload backup file: $filename"
res=`curl $box_upload_url --silent -X POST \
 -H "Authorization: Bearer $access_token" \
 -F attributes="{\"name\":\"$filename\", \"parent\":{\"id\":\"$parent_id\"}}" \
 -F file=@$filename`
ret=$?
if [ $ret -ne 0 ]; then
  echo "failed to upload `basename $filename`"
  exit 1
fi
echo "done."

echo "clean up..."
rm -rf $backup_dir || exit $?
rm -f $filename || exit $?

error=`echo $res | jq -r '.error'`
error_description=`echo $res | jq -r '.error_description'`
if [ "$error" != "null" ]; then
  echo "failed to upload file ($error): $error_description"
  exit 1
fi

exit 0
