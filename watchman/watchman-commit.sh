#!/bin/sh

jq=/usr/local/bin/jq

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=0

commit_log_file=/tmp/watchman-commit-message.log
github_url=http://git.gree-dev.net

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

  # commit git
  git commit --file $commit_log_file || exit $?
  commit_id=`git log -1 | head -1 | cut -c 8-`

  # git git push
  git pull --rebase origin $branch || exit $?
  git push origin master || exit_code=$?
  echo "automatic sync with git is done: $exit_code"

  # log
  `dirname $0`/../script/sonya.sh ":) git commit by `whoami`@`hostname`" $github_url/kms/asset/commit/$commit_id $commit_log_file || exit $?
fi

# git push return by 1 when master branch is updated
#exit $exit_code
exit 0
