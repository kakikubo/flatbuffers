#!/bin/sh

#chat_id=31065011  # personal dev
#chat_id=27838766  # KMSエンジニア
#chat_id=31118592  # KMSビルド
chat_id=35615824  # KMSアセット
text_file=/tmp/sonya.$$.text

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

echo "[info][title]$title[/title]$job_url[code]`tail -100 $log_file`[/code]$reference_url[/info]" > $text_file
`dirname $0`/sonya2.sh $chat_id $text_file
exit $?
