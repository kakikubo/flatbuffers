#!/bin/sh

jq=/usr/local/bin/jq
export PYTHONPATH=$PYTHONPATH:/usr/local/lib/python2.7

tool_dir=`pwd | sed -e 's/Box Sync/box/'`
top_dir=$1
sleep=$2
[ -n "$top_dir" ] || top_dir=`pwd`
[ -n "$sleep" ] || sleep=5

branch=master # git branch for kms/asset
target=`echo $WATCHMAN_ROOT | sed -e 's!.*/kms_\([^_]*\)_asset/.*!\1!'` # asset name
[ "$target" = "$WATCHMAN_ROOT" ] && target=unknown
message="$WATCHMAN_TRIGGER $LOGNAME@$WATCHMAN_ROOT (`date`)"

# logging
echo "\n\n\n\n\n---- $message"
read json
echo $json | $jq '.'

# sub shell
(
  # update spine
  files=`echo $json | $jq -r '.[]["name"]'`
  for file in $files; do
    if echo $file | grep 'spine/face/[^/]*/.*.png\|spine/weapon/.*.png'; then
      $tool_dir/script/spine-atlas-update.sh $top_dir || exit $?
      break
    fi
  done

  # build asset
  $tool_dir/script/build.py build --target $target || exit $?
  if [ $target = "master" ]; then
    for user_target in `ls ${tool_dir}/../box/users_generated`
    do
      if [ -d ${tool_dir}/../box/users_generated/${user_target} ]; then
        $tool_dir/script/build.py build --target $user_target || exit $?
      fi
    done
  fi

  # git commit + push
  if [ $target = "master" ]; then
    cd $top_dir

    # setup git
    current_branch=`git branch | cut -c 3-`
    if [ $current_branch != $branch ]; then
      echo "current branch is not $branch ($current_branch)"
      exit 1
    fi

    # git add + git rm
    git status --short | grep -e '^R[M\?]' | cut -f 4 -d ' ' | xargs git add || exit $?  # renamed + changed
    git status --short | grep -e '^.[M\?]' | cut -c 4-       | xargs git add || exit $?  # added + changed
    git status --short | grep -e '^.D'     | cut -c 4-       | xargs git rm  || exit $?  # deleted

    # commit git
    if git status | grep 'Changes to be committed:' > /dev/null; then
      echo "something to commit exists"
      #$tool_dir/watchman/watchman-commit.sh $sleep || exit $?  # blocking
      $tool_dir/watchman/watchman-commit.sh $sleep &  # non-blocking
    else
      echo "nothing to commit exists"
    fi
  fi
)
ret=$?
if [ $ret -ne 0 ]; then
  echo "some error occurred in build process: $ret"
  $tool_dir/script/sonya.sh "(devil) $ret: $message" $tool_dir/watchman/watchman-callback.log
fi

exit 0
