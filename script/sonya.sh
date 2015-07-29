#!/bin/sh

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
#chat_id=31065011  # personal dev
#chat_id=27838766  # KMSエンジニア
#chat_id=31118592  # KMSビルド
chat_id=35615824  # KMSアセット

title=$1
job_url=$2
log_file=$3
reference_url=$4
[ -n "$5" ] && chat_id=$5
if [ "$#" -lt 3 ]; then
  echo "$0 <title> <jenkins_job_url> <log_file> [<reference_url> [<chat_id>]]"
  echo "Chatwork Chat ID: $chat_id"
  exit 1
fi

gtimeout 10 curl --silent -F rid=$chat_id -F text="[info][title]$title[/title]$job_url[code]`tail -100 $log_file`[/code]$reference_url[/info]" $sonya_chan_url || exit $?
exit 0
