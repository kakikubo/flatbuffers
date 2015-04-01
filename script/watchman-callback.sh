#!/bin/sh

jq=/usr/local/bin/jq
branch=master
subdir=bundled/preload/files

echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | $jq '.'

# setup git
current_branch=`git branch | cut -c 3-`
if [ $current_branch != $branch ]; then
  echo "current branch is not $branch ($current_branch)"
  exit 1
fi

# added + changed
for f in `git status --short | grep -e '^.[M\?]' | cut -c 4- | grep $subdir`; do
  echo "$f is added"
  git add $f || exit $?
done

# deleted
for f in `git status --short | grep -e '^.D' | cut -c 4- | grep $subdir`; do
  echo "$f is deleted"
  git rm $f || exit $?
done

# commit git
if git status | grep 'Changes to be committed:' > /dev/null; then
  echo "something to commit exists"
  #hook/watchman-commit.sh || exit $?
  hook/watchman-commit.sh &
else
  echo "nothing to commit exists"
fi

exit 0
