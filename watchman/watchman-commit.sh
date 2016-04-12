#!/bin/sh

jq=/usr/local/bin/jq

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=0

sonya=`dirname $0`/../chatwork/sonya.sh
commit_log_file=/tmp/watchman-commit-message.log
github_url=http://git.gree-dev.net/kms/asset
jenkins_url="http://dev-kms.dev.gree.jp/jenkins/job/001_KMS_GHE_CommitHook/build"

excel_diff="`dirname $0`/../../ExcelDiffGenerator/excel-diff"
excel_diff_root_url="http://g-pc-00363221.intra.gree-office.net/excel-diff"
excel_diff_dir=/var/www/excel-diff
excel_diff_url=

build_log_file=/tmp/watchman-build-message.log
asset_chat_id=35615824 # KMSアセット
build_chat_id=31118592 # KMSビルド

exit_code=0
if git status | grep 'Changes to be committed:' > /dev/null; then
  sleep $sleep # wait to sync complete
  pre_commit_id=`git log -1 | head -1 | cut -c 8-`

  # commit log
  echo "git commit and push (committed by $self `whoami`@`hostname`)"
  git status --short | grep -e '^[MADR]' > $commit_log_file || exit $?
  echo "committed by $self `whoami`@`hostname`" >> $commit_log_file

  # get xlsx diff
  for i in `git status --short | grep -e '^[MA]' | grep .xlsx | cut -c 4-`; do
    echo >> $commit_log_file
    git diff --cached $i >> $commit_log_file || exit $?
  done

  # get md5 diff
  rm -f $build_log_file
  for i in `git status --short | grep -e '^[MA]' | grep _md5.h | cut -c 4-`; do
    echo $i >> $build_log_file
    #git diff --cached $i >> $commit_log_file || exit $?
    curl $jenkins_url -X POST --form json='{"parameter": []}' || exit $?
  done

  # commit git
  git commit --file $commit_log_file || exit $?
  commit_id=`git log -1 | head -1 | cut -c 8-`

  # excel diff
  excel_diff_url=
  if grep .xlsx $commit_log_file; then
    excel_diff_html=excel-diff.$pre_commit_id..$commit_id.html
    $excel_diff . $pre_commit_id..$commit_id --ng >> $excel_diff_dir/$excel_diff_html || exit $?
    excel_diff_url=$excel_diff_root_url/$excel_diff_html
  fi

  # git git push
  git pull --rebase origin $branch || exit $?
  git push origin $branch || exit_code=$?
  echo "automatic sync with git is done: $exit_code"

  # log
  icon=":)"
  grep -q -e '^D' $commit_log_file && icon="(devil)(devil)(devil)"
  $sonya $asset_chat_id "[info][title]$icon git commit by `whoami`@`hostname`[/title]$github_url/commit/$commit_id[code]`cat $commit_log_file`[/code]$excel_diff_url[/info]" || exit $?
  if [ -s $build_log_file ]; then
    echo "=== C++ Header File is updated === " >> $build_log_file
    $sonya  $build_chat_id "[info][title](F) C++ header file is updated. Please clean build your app[/title]$github_url/commit/$commit_id[code]`cat $build_log_file`[/code]$github_url[/info]" || exit $?
  fi
fi

# git push return by 1 when master branch is updated
#exit $exit_code
exit 0
