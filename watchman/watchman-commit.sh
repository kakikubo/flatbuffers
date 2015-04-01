#!/bin/sh

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=5

commit_log_file=/tmp/watchman-commit-message.log

if pgrep -fl $self; then
  echo "other $self is running. abort..."
  exit 0
fi

if git status | grep 'Changes to be committed:' > /dev/null; then
  sleep $sleep # wait to sync complete

  echo "git commit and push (committed by $self `hostname`:$WATCHMAN_ROOT)"
  git status --short | grep -e '^[MAD]' > $commit_log_file
  echo "committed by $self `hostname`:$WATCHMAN_ROOT" >> $commit_log_file
  git commit --file $commit_log_file || exit $?
  git pull --rebase origin $branch|| exit $?
  git push origin master || exit $?
  echo "automatic sync with git is done"
fi

exit 0
