#!/bin/sh
# -*- coding: utf-8 -*-
# vim: ai, ts=2, sw=2, et, hlsearch

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
#chat_id=31065011  # personal dev
#chat_id=27838766  # KMSエンジニア
chat_id=31118592  # KMSビルド
hockeyapp_url=

log_file=/tmp/hockeyapp-webhook.log
date >> $log_file
export >> $log_file

if [ -n "$REQUEST_BODY" ]; then
  _type=`  echo $REQUEST_BODY | jq -r '.type'`
  title=`  echo $REQUEST_BODY | jq -r '.title'`
  url=`    echo $REQUEST_BODY | jq -r '.url'`
  text=`   echo $REQUEST_BODY | jq -r '.text'`
  sent_at=`echo $REQUEST_BODY | jq -r '.sent_at'`
  icon=""
  code=""

  if [ "$_type" = "app_version" ]; then
    icon=":)"
    version=`echo $REQUEST_BODY | jq -r '.app_version["version"]'`
    shortversion=`echo $REQUEST_BODY | jq -r '.app_version["shortversion"]'`
    device_family=`echo $REQUEST_BODY | jq -r '.app_version["device_family"]'`
    appsize=`echo $REQUEST_BODY | jq -r '.app_version["appsize"]'`
    code=$(cat <<END
Version: $version
Short Version: $shortversion
Device: $device_family
Size: $appsize Byte
END
)
  elif [ "$_type" = "crash_reason" ]; then
    icon=";("
    app_version_id=`echo $REQUEST_BODY | jq -r '.crash_reason["app_version_id"]'`
    exception_type=`echo $REQUEST_BODY | jq -r '.crash_reason["exception_type"]'`
    reason=`echo $REQUEST_BODY | jq -r '.crash_reason["reason"]'`
    file=`echo $REQUEST_BODY | jq -r '.crash_reason["file"]'`
    line=`echo $REQUEST_BODY | jq -r '.crash_reason["line"]'`
    method=`echo $REQUEST_BODY | jq -r '.crash_reason["method"]'`
    class=`echo $REQUEST_BODY | jq -r '.crash_reason["class"]'`
    last_crash_at=`echo $REQUEST_BODY | jq -r '.crash_reason["last_crash_at"]'`
    code=$(cat <<END
Time: $last_crash_at
Version ID: $app_version_id
Exception Type: $exception_type
Reason: $reason
File: $file:$line $class
Method: $method
END
)
  elif [ "$_type" = "ping" ]; then
    icon="(y)"
    code=`echo $REQUEST_BODY | jq '.ping'`
  fi

  if [ -n "$code" ]; then
    timeout 10 curl --silent -F rid=$chat_id -F text="[info][title]$icon $title: $sent_at[/title]$text[code]$code[/code]$url[/info]" $sonya_chan_url || exit $?
  fi
fi

echo "Content-type:text/html\r\n"
echo "<html><head>"
echo "<title>$NAME</title>"
echo '<meta name="description" content="'$NAME'">'
echo '<meta name="keywords" content="'$NAME'">'
echo '<meta http-equiv="Content-type"
content="text/html;charset=UTF-8">'
echo '<meta name="ROBOTS" content="noindex">'
echo "</head><body><pre>"
echo "type = $_type"
echo "title = $title"
echo "sent_at = $sent_at"
echo "text = $text"
echo "url = $url"
echo "code = $code"
echo "</pre></body></html>"
