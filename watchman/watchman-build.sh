#!/bin/sh

tool_dir=`pwd | sed -e 's/Box Sync/box/'`
git_dir=`ls -1d /Users/jenkins/*/asset | head -1 2>/dev/null`

target=$1
[ -n "$target" ] || exit 1

# build asset
$tool_dir/script/build.py build $target --git-dir $git_dir || exit $?
echo "build $target done"

if [ $target = "master" ]; then
  # git commit + push
  cd $git_dir

  # setup git
  current_branch=`git branch | grep '^*' | cut -c 3-`
  if [ $current_branch != 'master' ]; then
    echo "current branch is not master ($current_branch)"
    exit 1
  fi

  # check box conflicted files
  cwd=`pwd`
  invalid_file_count=`find $cwd -name '* (*).*' | wc -l`
  if [ $invalid_file_count -gt 0 ]; then
    echo "=== Box Sync conflicted files are found: cannot commit to git"
    find `pwd` -name '* (*).*'
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

echo "--- WATCHMAN BUILD SUCCESS ----"
exit 0
