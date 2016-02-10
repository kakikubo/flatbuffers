#!/bin/sh

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
#sonya_chan_url=http://takochan.gree-dev.net:4979/send_chat

chat_id=$1
text=$2
if [ "$#" -ne 2 ]; then
  echo "$0 <chat_id> <text|text_file>"
  exit 1
fi

if [ -f "$text" ]; then
  gtimeout 10 curl --silent -F rid=$chat_id -F text="`cat $text`" $sonya_chan_url
else
  gtimeout 10 curl --silent -F rid=$chat_id -F text="$text" $sonya_chan_url
fi
exit $?
