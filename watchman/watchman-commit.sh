#!/bin/sh

jq=/usr/local/bin/jq

self=`basename $0`
branch=master
sleep=$1
[ -n "$sleep" ] || sleep=0

commit_log_file=/tmp/watchman-commit-message.log
gitlab_url=http://git.gree-dev.net
version_manifest=manifests/dev/version.manifest
version_tag=

if pgrep -fl $self; then
  echo "other $self is running. abort..."
  exit 0
fi

exit_code=0
if git status | grep 'Changes to be committed:' > /dev/null; then
  sleep $sleep # wait to sync complete

  # commit git
  echo "git commit and push (committed by $self `hostname`:$WATCHMAN_ROOT)"
  git status --short | grep -e '^[MAD]' > $commit_log_file
  echo "committed by $self `hostname`:$WATCHMAN_ROOT" >> $commit_log_file
  git commit --file $commit_log_file || exit $?
  commit_id=`git log -1 | head -1 | cut -c 8-`

  # append commit id to version + tag
  if grep $version_manifest $commit_log_file; then
    cat $version_manifest | $jq ".version = .version + \" $commit_id\"" > $version_manifest.tmp
    mv $version_manifest.tmp $version_manifest || exit $?
    git add $version_manifest || exit $?
    git commit --amend --file $commit_log_file || exit $?

    version_tag=`cat $version_manifest | $jq -r ".version" | sed -e 's/[ :]/-/g'`
    git tag $version_tag || exit $?
  fi

  # git git push
  git pull --rebase origin $branch || exit $?
  git push origin master || exit_code=$?
  [ -n "$version_tag" ] && git push origin $version_tag || exit_code=$?
  echo "automatic sync with git is done: $exit_code"

  # log
  `dirname $0`/../script/sonya.sh ":) `hostname`:$WATCHMAN_ROOT" $commit_log_file $gitlab_url/kms/asset/commit/$commit_id || exit $?
fi

exit $exit_code
