#!/bin/sh

usage() {
  cat <<END
$0 <src box dir> <dest s3 bucket> <git repository>

update kms official website 

Public URL: http://another-eden.jp
Git Repository: https://git.gree-dev.net/kms/website
Box: https://gree-office.box.com/s/3onitj85ypovmnhoun3jiwcrxuxripms
END
}

while getopts p:h OPT; do
  case $OPT in
    p) profile=$OPTARG; exit 0;;
    h) usage; exit 0;;
    *) usage; exit 1;;
  esac
done
shift $((OPTIND - 1))

if [ "$#" -gt 3 ]; then
  echo "invalid arguments: $*"
  usage
  exit 1
fi
src_dir=${1:-/Users/jenkins/box/kms-website}
git_dir=${2:-/Users/jenkins/kms/website}
dest_url=${3:-s3://gree-kms-website}

profile=${profile:-website}
sonya=`pwd`/`dirname $0`/sonya.sh
commit_log_file=/tmp/update-website.log
github_url=http://git.gree-dev.net/kms/website
website_url=https://another-eden.jp
chat_id=41368241

## sync box to git working dir
rsync_options="-ac --exclude .DS_Store --exclude '.*' --exclude .git --delete"
rsync $rsync_options $src_dir/ $git_dir/ || exit $?

## update git
cd $git_dir
# setup git
current_branch=`git branch | grep '^*' | cut -c 3-`
if [ $current_branch != 'master' ]; then
  echo "current branch is not master ($current_branch)"
  exit 1
fi

# git add + git rm
git status --short | grep -e '^R[M\?]' | cut -f 4 -d ' ' | xargs git add || exit $?  # renamed + changed
git status --short | grep -e '^.[M\?]' | cut -c 4-       | xargs git add || exit $?  # added + changed
git status --short | grep -e '^.D'     | cut -c 4-       | xargs git rm  || exit $?  # deleted

exit_code=0
if git status | grep 'Changes to be committed:' > /dev/null; then

  # commit log
  echo "git commit and push (committed by $self `whoami`@`hostname`)"
  git status --short | grep -e '^[MAD]' > $commit_log_file || exit $?
  echo "committed by $self `whoami`@`hostname`" >> $commit_log_file

  # commit git
  git commit --file $commit_log_file || exit $?
  commit_id=`git log -1 | head -1 | cut -c 8-`

  # git git push
  git pull --rebase origin $branch || exit $?
  git push origin $branch || exit_code=$?
  echo "automatic sync with git is done: $exit_code"

  # report to sonya
  $sonya ":) update another-eden.jp website by `whoami`@`hostname`" $github_url/commit/$commit_id $commit_log_file $website_url $chat_id || exit $?

  # deploy to S3
  # without --delete
  s3_options="--profile $profile --exclude .DS_Store --exclude .gitignore"
  aws s3 sync $s3_options $src_dir $dest_url || exit $?
fi
exit 0
