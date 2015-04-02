#!/bin/sh

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
#chat_id=31065011  # personal dev
#chat_id=27838766  # KMSエンジニア
chat_id=31118592  # KMSビルド

curl --silent -F rid=$chat_id -F text="[info][title]$1[/title]`hostname`:$2[code]`tail $2`[/code]$3[/info]" $sonya_chan_url || exit $?
exit 0
