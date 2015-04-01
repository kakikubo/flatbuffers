#!/bin/sh

self=`basename $0`
branch=master

if pgrep -fl $self; then
  echo "other $self is running. abort..."
  exit 0
fi

if git status | grep 'Changes to be committed:' > /dev/null; then
  sleep 5 # wait to sync complete

  echo "git commit and push (committed by $self `hostname`:$WATCHMAN_ROOT)"
  git commit -m "committed by $self `hostname`:$WATCHMAN_ROOT" || exit $?
  git pull --rebase origin $branch|| exit $?
  git push origin master || exit $?
  echo "automatic sync with git is done"
fi

exit 0
