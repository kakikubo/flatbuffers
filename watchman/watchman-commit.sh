#!/bin/sh

jq=/usr/local/bin/jq

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=0

sonya=`dirname $0`/../script/sonya.sh
commit_log_file=/tmp/watchman-commit-message.log
github_url=http://git.gree-dev.net

build_log_file=/tmp/watchman-build-message.log
build_chat_id=31118592 # KMSビルド

if pgrep -fl $self; then
  echo "other $self is running. abort..."
  exit 0
fi

exit_code=0
if git status | grep 'Changes to be committed:' > /dev/null; then
  sleep $sleep # wait to sync complete

  # commit log
  echo "git commit and push (committed by $self `whoami`@`hostname`)"
  git status --short | grep -e '^[MAD]' > $commit_log_file || exit $?
  echo "committed by $self `whoami`@`hostname`" >> $commit_log_file

  # get xlsx diff
  for i in `git status --short | grep -e '^[MA]' | grep .xlsx | cut -c 4-`; do
    echo >> $commit_log_file
    git diff --cached $i >> $commit_log_file || exit $?
  done

  # get md5 diff
  rm -f $build_log_file
  for i in `git status --short | grep -e '^[MA]' | grep .md5 | cut -c 4-`; do
    echo $i >> $build_log_file
    #git diff --cached $i >> $commit_log_file || exit $?
  done

  # commit git
  git commit --file $commit_log_file || exit $?
  commit_id=`git log -1 | head -1 | cut -c 8-`

  # git git push
  git pull --rebase origin $branch || exit $?
  git push origin $branch || exit_code=$?
  echo "automatic sync with git is done: $exit_code"

  # log
  $sonya ":) git commit by `whoami`@`hostname`" $github_url/kms/asset/commit/$commit_id $commit_log_file || exit $?
  if [ -s $build_log_file ]; then
    echo "=== C++ Header File is updated === " >> $build_log_file
    $sonya "(F) C++ header file is updated. Please clean build your app" $github_url/kms/asset/commit/$commit_id $build_log_file $github_url/kms/asset $build_chat_id || exit $?
  fi
fi

# git push return by 1 when master branch is updated
#exit $exit_code
exit 0
