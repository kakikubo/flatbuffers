#/bin/bash
commit_id=`git log | head -1 | cut -c 8-`
job_url=
if [ `whoami` = 'jenkins' ]; then
  job_url=$JENKINS_URL/job/$JOB_NAME/$BUILD_ID
fi
git_url=`git config --get remote.origin.url | sed -ne 's!git@\(.*\):\(.*\).git!https://\1/\2!p'` # git -> https

sonya_file=$1
title=${2:-(devil) jenkins build ERROR!!! in $BUILD_ID ($JOB_NAME)}
chat_id=${3:-31118592}  # KMS ビルド

`dirname $0`/sonya.sh $chat_id "[info][title]$title[/title]$job_url[code]`tail -100 $sonya_file`[/code]$git_url/commit/$commit_id[/info]"
exit $?
