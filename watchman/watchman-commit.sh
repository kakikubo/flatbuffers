#!/bin/sh

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=5

commit_log_file=/tmp/watchman-commit-message.log
gitlab_url=http://g-pc-4114.intra.gree-office.net:3000

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

  commit_id=`git log | head -1 | cut -c 8-`
  `dirname $0`/../script/sonya.sh "`hostname`:$WATCHMAN_ROOT" $commit_log_file $gitlab_url/kms/asset/commit/$commit_id || exit $?
fi

exit 0
