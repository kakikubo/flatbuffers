#!/bin/sh

jq=/usr/local/bin/jq
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

sleep=$1
[ -n "$sleep" ] || sleep=5

branch=master # git branch for kms/asset
target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = $WATCHMAN_ROOT ] && target=unknown

# logging
echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | $jq '.'

# update spine
if [ $WATCHMAN_TRIGGER = 'spine' ]; then
  hook/spine-atlas-update.sh || exit $?
fi

# build master-data
hook/build.py build --target $target || exit $?

# git commit + push
if [ $target = "master" ]; then
  # setup git
  current_branch=`git branch | cut -c 3-`
  if [ $current_branch != $branch ]; then
    echo "current branch is not $branch ($current_branch)"
    exit 1
  fi

  subdirs="master bundled/preload/files"
  for subdir in $subdirs; do
    # added + changed
    for f in `git status --short $subdir | grep -e '^.[M\?]' | cut -c 4-`; do
      echo "$f is added"
      git add $f || exit $?
    done

    # deleted
    for f in `git status --short $subdir | grep -e '^.D' | cut -c 4-`; do
      echo "$f is deleted"
      git rm $f || exit $?
    done
  done

  # commit git
  if git status | grep 'Changes to be committed:' > /dev/null; then
    echo "something to commit exists"
    #hook/watchman-git-commit.sh $sleep || exit $?  # blocking
    hook/watchman-git-commit.sh $sleep &  # non-blocking
  else
    echo "nothing to commit exists"
  fi
fi

exit 0
