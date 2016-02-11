#!/bin/sh

source `dirname $0`/box-config.sh
access_token=`git config box.accesstoken`
chatwork_to=`dirname $0`/../script/chatwork_to.sh

function box() {
  curl --silent -H "Authorization: Bearer $access_token" $box_api_url/$1
  return $?
}

id=0
current=
for i in ${1//\// }; do
  ret=`box folders/$id/items | jq -r ".entries[] | if .name == \"$i\" then .id else empty end"`
  if [ -n "$ret" ]; then
    id=$ret
  else
    for file_id in `box folders/$id/items | jq -r ".entries[].id"`; do
      modified_by=`box files/$file_id | jq -r '.name, .modified_by.login' | cut -d '@' -f 1`
      file=`echo $modified_by | cut -d ' ' -f 1`
      user=`echo $modified_by | cut -d ' ' -f 2`
      echo "`$chatwork_to $user`: $current/$file"
    done
  fi
  current=$current/$i
done

exit 0
