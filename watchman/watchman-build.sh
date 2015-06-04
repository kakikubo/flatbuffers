#!/bin/sh

tool_dir=`pwd | sed -e 's/Box Sync/box/'`
asset_list_json=/var/www/cdn/dev.asset_list.json

target=$1
git_dir=$2
[ -n "$target" ]   || exit 1
[ -n "$git_dir" ]  || git_dir=`pwd`

# build asset
$tool_dir/script/build.py build --target $target || exit $?

if [ $target = "master" ]; then
  # update each user in master updated
  for user_target in `cat $asset_list_json | jq '.[]' -r`; do
    $tool_dir/script/build.py build --target $user_target || exit $?
  done

  # git commit + push
  cd $git_dir

  # setup git
  current_branch=`git branch | cut -c 3-`
  if [ $current_branch != 'master' ]; then
    echo "current branch is not master ($current_branch)"
    exit 1
  fi

  # git add + git rm
  git status --short | grep -e '^R[M\?]' | cut -f 4 -d ' ' | xargs git add || exit $?  # renamed + changed
  git status --short | grep -e '^.[M\?]' | cut -c 4-       | xargs git add || exit $?  # added + changed
  git status --short | grep -e '^.D'     | cut -c 4-       | xargs git rm  || exit $?  # deleted

  # commit git
  if git status | grep 'Changes to be committed:' > /dev/null; then
    echo "something to commit exists"
    $tool_dir/watchman/watchman-commit.sh || exit $?  # blocking
  else
    echo "nothing to commit exists"
  fi
fi

exit 0
