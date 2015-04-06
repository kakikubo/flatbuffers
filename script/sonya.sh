#!/bin/sh

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
#chat_id=31065011  # personal dev
#chat_id=27838766  # KMSエンジニア
chat_id=31118592  # KMSビルド

title=$1
log_file=$2
reference_url=$3
[ -n "$4" ] && chat_id=$4
if [ "$#" -lt 2 ]; then
  echo "$0 <title> <log_file> [<reference_url> [<chat_id>]]"
  echo "Chatwork Chat ID: $chat_id"
  exit 1
fi

curl --silent -F rid=$chat_id -F text="[info][title]$title[/title]`hostname`:$log_file[code]`tail -30 $log_file`[/code]$reference_url[/info]" $sonya_chan_url || exit $?
exit 0
