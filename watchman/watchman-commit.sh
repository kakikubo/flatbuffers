#!/bin/sh

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=5

if pgrep -fl $self; then
  echo "other $self is running. abort..."
  exit 0
fi

if git status | grep 'Changes to be committed:' > /dev/null; then
  sleep $sleep # wait to sync complete

  echo "git commit and push (committed by $self `hostname`:$WATCHMAN_ROOT)"
  files=`git status --short | grep -e '^[MAD]'`
  git commit -m "$files\ncommitted by $self `hostname`:$WATCHMAN_ROOT" || exit $?
  git pull --rebase origin $branch|| exit $?
  git push origin master || exit $?
  echo "automatic sync with git is done"
fi

exit 0
