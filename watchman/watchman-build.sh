#!/bin/sh

tool_dir=`pwd | sed -e 's/Box Sync/box/'`
git_dir=/Users/kms.jenkins/kms/asset
asset_list_json=$git_dir/manifests/dev.asset_list.json
vagrant_dir=/Users/kms.jenkins/kms/provisioning
in_vagrant_dir=/vagrant
user_version=0.0.1

target=$1
[ -n "$target" ] || exit 1

# build asset
$tool_dir/script/build.py build $target --git-dir $git_dir || exit $?
echo "build $target done"

if [ $target = "master" ]; then
  # update each user in master updated
  #for user_target in `cat $asset_list_json | jq '.[]' -r`; do
  #  $tool_dir/script/build.py build --target $user_target
  #  if [ $? -ne 0 ]; then
  #    echo "*** build $user_target via master failed ***"
  #    #exit 1	# ignore other user error
  #  fi
  #  echo "build $user_target done"
  #done

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

  # build user data default
  echo "install user data default"
  cd $vagrant_dir
  rsync -a --delete $git_dir/user_data/ user_data || exit $?
  vagrant ssh -- $in_vagrant_dir/app/server/cli/userdata.php -s develop install-default $user_version $in_vagrant_dir/user_data/default.json || exit $?
fi

exit 0
