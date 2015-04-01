#!/bin/sh

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
#chat_id=31065011  # personal dev
chat_id=27838766  # KMSエンジニア

curl -F rid=$chat_id -F text="[info][title]$1[/title][code]`tail $2`[/code][/info]" $sonya_chan_url || exit $?
exit 0
