#!/bin/sh

jq=/usr/local/bin/jq
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

tool_dir=`pwd`
top_dir=$1
sleep=$2
[ -n "$top_dir" ] || top_dir=`pwd`
[ -n "$sleep" ] || sleep=5

branch=master # git branch for kms/asset
target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = $WATCHMAN_ROOT ] && target=unknown

# logging
echo "\n\n\n\n\n---- $WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"
read json
echo $json | $jq '.'

# update spine
files=`echo $json | jq -r '.[]["name"]'`
for file in $files; do
  if echo $file | grep 'spine/'; then
    $tool_dir/script/spine-atlas-update.sh || exit $?
    break
  fi
done

# build master-data
$tool_dir/script/build.py build --target $target || exit $?

# git commit + push
if [ $target = "master" ]; then
  cd $top_dir

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
    #$tool_dir/watchman/watchman-git-commit.sh $sleep || exit $?  # blocking
    $tool_dir/watchman/watchman-git-commit.sh $sleep &  # non-blocking
  else
    echo "nothing to commit exists"
  fi
fi

exit 0
