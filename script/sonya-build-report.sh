#/bin/bash
commit_id=`git log | head -1 | cut -c 8-`
job_url=http://dev-kms.dev.gree.jp/jenkins/job/$JOB_NAME/$BUILD_ID
git_url=https://git.gree-dev.net/kms/client/commit/$commit_id
chat_id=31118592
sonya_file=$1
title=$2
[ -n "$title" ] || title="(devil) jenkins build ERROR!!! in $BUILD_ID ($JOB_NAME)"
/Users/kms.jenkins/box/tool/script/sonya.sh "$title" $git_url $sonya_file $job_url $chat_id
exit $?
