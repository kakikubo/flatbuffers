#!/bin/sh
# -*- coding: utf-8 -*-
# vim: ai, ts=2, sw=2, et, hlsearch

sonya_chan_url=http://skail.gree-dev.net:4979/send_chat
log_file=/tmp/github-webhook.log
date >> $log_file
export >> $log_file

message_file=/tmp/github-webhook-message.text

if [ "$REQUEST_METHOD" = "POST" ]; then
  [ -z "$REQUEST_BODY" ] && exit 1
  case $HTTP_X_GITHUB_EVENT in
    push)
      ref=`echo $REQUEST_BODY | jq -r '.ref'`
      case $ref in
        refs/heads/master)
          chat_id=44255707 # KMS リリース
          icon="(F)"
          text=
          repository=`echo $REQUEST_BODY | jq -r '.repository.full_name'`
          github_url=`echo $REQUEST_BODY | jq -r '.repository.url'`
          compare=`echo $REQUEST_BODY | jq -r '.compare'`
          committers=`echo $REQUEST_BODY | jq -r '.commits[].committer.username' | sort | uniq`
          chatwork_users=
          for i in $committers; do
            user=`echo $i | tr '-' '.'`
            user=`jq -r ".[\"$user\"]" chatwork-users.json | grep -v null`
            [ -n "$user" ] && chatwork_users="$chatwork_users $user"
          done
          echo $REQUEST_BODY | jq -r '.commits[].message' | sed -n -e 's/^Merge pull request \(.*\)$/\1/p' > $message_file
          if [ -s $message_file ]; then
            pull_requests=
            while read l; do
              id=`echo $l | sed -n -e 's/.*#\([0-9]*\).*/\1/p'`
              pull_requests="${pull_requests:+$pull_requests}$l - $github_url/pull/$id"
            done < $message_file
            text="$chatwork_users[info][title]$icon Pull requests are merged into '$repository' '$ref'[/title]$compare[code]$committers[/code]$pull_requests[/info]"
            timeout 10 curl --silent -F rid=$chat_id -F text="$text" $sonya_chan_url || exit $?
            timeout 10 curl -X POST http://dev-kms.dev.gree.jp/jenkins/job/002_KMS_Client_GitPrRelease/build
            timeout 10 curl -X POST http://dev-kms.dev.gree.jp/jenkins/job/031_KMS_Dev_iOS_For_HockeyApp/build
          fi
          ;;
        refs/heads/develop)
          chat_id=44255707 # KMS リリース
          icon="(handshake)"
          repository=`echo $REQUEST_BODY | jq -r '.repository.full_name'`
          compare=`echo $REQUEST_BODY | jq -r '.compare'`
          url=`echo $REQUEST_BODY | jq -r '.head_commit.url'`
          message=`echo $REQUEST_BODY | jq -r '.head_commit.message'`
          modified=`echo $REQUEST_BODY | jq -r '.head_commit.modified[]'`
          text="[info][title]$icon Pushed into '$repository' '$ref'[/title]commit: $urlcompare: $compare[code]$modified[/code]$message[/info]"
          timeout 10 curl --silent -F rid=$chat_id -F text="$text" $sonya_chan_url || exit $?
          ;;
        *)
          ;;
      esac
      ;;
    ping)
      ;;
    pull_request|*)
      chat_id=44255707 # KMS リリース
      repository=`echo $REQUEST_BODY | jq -r '.repository.full_name'`
      action=`echo $REQUEST_BODY | jq -r '.action'`
      sender=`echo $REQUEST_BODY | jq -r '.sender.login'`
      number=`echo $REQUEST_BODY | jq -r '.pull_request.number'`
      state=`echo $REQUEST_BODY | jq -r '.pull_request.state'`
      html_url=`echo $REQUEST_BODY | jq -r '.pull_request.html_url'`
      title=`echo $REQUEST_BODY | jq -r '.pull_request.title'`
      body=`echo $REQUEST_BODY | jq -r '.pull_request.body'`
      user=`echo $REQUEST_BODY | jq -r '.pull_request.user.login'`
      chatwork_user=`echo $user | tr '-' '.'`
      chatwork_to=`jq -r ".[\"$chatwork_user\"]" chatwork-users.json | grep -v null`
      case $action in
        opened) icon="(*)";;
        labeled) icon="(:^)";;
        synchronize) icon="";;
        *) icon="(:/)";;
      esac
      if [ -n "$icon" ]; then
        echo "$chatwork_to[info][title]$icon Pull Request '$number' for '$repository' by '$user' is '$action' by '$sender'[/title]$html_url ($state)[title]$title[/title]$body[/info]$HTTP_X_GITHUB_EVENT" > $message_file
        timeout 10 curl --silent -F rid=$chat_id -F text="`cat $message_file`" $sonya_chan_url || exit $?
      fi
      ;;
  esac
fi

echo "Content-type:text/html\r\n"
echo "<html><head>"
echo "<title>Github Webook</title>"
echo '<meta http-equiv="Content-type" content="text/html;charset=UTF-8">'
echo '<meta name="ROBOTS" content="noindex">'
echo "</head><body><pre>"
echo $REQUEST_BODY | jq '.'
echo "</pre></body></html>"
