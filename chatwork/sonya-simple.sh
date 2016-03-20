#!/bin/sh

#chat_id=31065011  # personal dev
#chat_id=27838766  # KMSエンジニア
#chat_id=31118592  # KMSビルド
chat_id=35615824  # KMSアセット
text_file=/tmp/sonya.$$.text

chat_id=${1:-$chat_id}
title=$2
log_file=$3
job_url=$4
reference_url=$5
if [ "$#" -lt 3 ]; then
  echo "$0 <chat_id> <title> <log_file> [<jenkins_job_url> [<reference_url>]]"
  echo "Chatwork Chat ID: $chat_id"
  exit 1
fi

`dirname $0`/sonya.sh $chat_id "[info][title]$title[/title]$job_url[code]`tail -100 $log_file`[/code]$reference_url[/info]"
exit $?
