#!/bin/sh
# -*- coding: utf-8 -*-
# vim: ai, ts=2, sw=2, et, hlsearch

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
log_file=/tmp/box-webhook.log
date >> $log_file
export >> $log_file

chat_id=43863580  # KMS Box Update Stream Timeline
sub_chat_id=45131101 # KMS Excel Lock

if [ -n "$QUERY_STRING" ]; then
  for kv in `echo $QUERY_STRING | sed -e 's/&/ /g'`; do
    key=`echo "$kv" | sed -e "s/\(.*\)=.*/\1/"`
    value=`echo "$kv" | sed -e "s/.*=\(.*\)/\1/"`

    case $key in
      item_name) item_name=$value;;
      item_description) item_description=$value;;
      item_id) item_id=$value;;
      item_parent_folder_id) item_parent_folder_id=$value;;
      event_type) event_type=$value;;
      from_user_name) from_user_name=$value;;
      item_extension) item_extension=$value;;
      *) ;;
    esac
  done

  icon=
  case $event_type in
    sent)     status="S" icon="("       message="送りました";;
    created)  status="A" icon="(*)"     message="作成しました";;
    uploaded) status="U" icon="8-|"     message="アップロードしました";;
    moved)    status="R" icon="8-)"     message="移動しました";;
    copied)   status="C" icon="(emo)"   message="コピーしました";;
    deleted)  status="D" icon="(devil)" message="削除しました";;
    locked)   status="L" icon="(bow)"   message="ロックしました";;
    unlocked) status="l" icon="(dance)" message="ロック解除しました";;
    *)        status="?" icon="(puke)"  message="操作しました";;
  esac

  user=`echo $from_user_name | tr '[:upper:]' '[:lower:]' | tr '+' '.'`
  chatwork_to=`jq -r ".[\"$user\"]" chatwork-users.json`

  text_file=/tmp/box-webhook.text
  cat >$text_file <<END
${chatwork_to:-$user}[info][title]$icon '$item_name' is '$event_type' by '$from_user_name'[/title]$from_user_name が $item_name を$message[code]$status $item_name (ID: $item_id)[/code]https://gree-office.app.box.com/files/0/f/$item_parent_folder_id[/info]
END

  timeout 10 curl --silent -F rid=$chat_id -F text="`cat $text_file`" $sonya_chan_url || exit $?
  if [ "$item_parent_folder_id" = '5528050009' -a "$item_extension" = "xlsx" ]; then
    timeout 10 curl --silent -F rid=$sub_chat_id -F text="`cat $text_file`" $sonya_chan_url || exit $?
  fi
fi

echo "Content-type:text/html\r\n"
echo "<html><head>"
echo "<title>Box Webhook</title>"
echo '<meta http-equiv="Content-type" content="text/html;charset=UTF-8">'
echo '<meta name="ROBOTS" content="noindex">'
echo "</head><body><pre>"
cat <<END
item_name=$item_name
item_id=$item_id
item_parent_folder_id=$item_parent_folder_id
event_type=$event_type
from_user_name=$from_user_name
item_extension=$item_extension
user=$user
chatwork_to=$chatwork_to
END
echo "</pre></body></html>"
exit 0
