#!/bin/sh

usage() {
  cat <<END
$0 [-p <profile>] [-s <sonya script>] [-w] <src box dir> <dest git repository dir> <dest s3 bucket url>

update kms official website 

Public URL: http://another-eden.jp
Git Repository: https://git.gree-dev.net/kms/website
Box: https://gree-office.box.com/s/3onitj85ypovmnhoun3jiwcrxuxripms
Box Sync: ~/Box\ Sync/kms-website
END
}

while getopts p:s:wh OPT; do
  case $OPT in
    p) profile=$OPTARG;;
    s) sonya=$OPTARG;;
    w) do_wait=1;;
    h) usage; exit 0;;
    *) usage; exit 1;;
  esac
done
shift $((OPTIND - 1))

if [ "$#" -gt 4 ]; then
  echo "invalid arguments: $*"
  usage
  exit 1
fi
src_dir=${1:-~/box/kms-website}
git_dir=${2:-~/kms/website}
dest_url=${3:-s3://gree-kms-website}
profile=${profile:-website}
sonya=${sonya:-~/kms/tool/script/sonya.sh}

commit_log_file=/tmp/update-website.log
github_url=http://git.gree-dev.net/kms/website
website_url=https://another-eden.jp
chat_id=41368241
distribution_id=EKOW6U3D7COMS
create_invalidation_json=/tmp/update-website-create-invalidation.json
invalidation_json=/tmp/update-website-invalidation.json
caller_reference="`basename $0`-`hostname`-`date +%Y%m%d_%H%M%S`"

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

  # correct updated files
  quantity=0
  items=
  for file in `git status --short | grep -e '^[MADR]' | cut -c 4-`; do
    quantity=$((quantity+1))
    items="${items:+$items,}\"/$file\""
  done
  cat > $create_invalidation_json <<END
{
  "DistributionId": "$distribution_id",
  "InvalidationBatch": {
    "Paths": {
      "Quantity": $quantity,
      "Items": [$items]
    },
    "CallerReference": "$caller_reference"
  }
}
END

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

  # deploy to S3
  # without --delete
  s3_options="--profile $profile --exclude .DS_Store --exclude .gitignore"
  aws s3 sync $s3_options $src_dir $dest_url || exit $?

  # invalidate cloud front contents cache
  cat $create_invalidation_json
  cloudfront_options="--profile $profile"
  aws cloudfront create-invalidation $cloudfront_options --cli-input-json file://$create_invalidation_json > $invalidation_json || exit $?
  invalidation_id=`jq -r '.Invalidation.Id' $invalidation_json` || exit $?

  # report to sonya
  $sonya ":) update another-eden.jp website by `whoami`@`hostname`" $github_url/commit/$commit_id $commit_log_file $website_url $chat_id || exit $?

  # wait invalidation
  if [ -n "$do_wait" ]; then
    status=`aws cloudfront get-invalidation $cloudfront_options --distribution-id $distribution_id --id $invalidation_id | jq -r '.Invalidation.Status'`
    if [ "$status" = "InProgress" ]; then
      aws cloudfront wait invalidation-completed $cloudfront_options --distribution-id $distribution_id --id $invalidation_id || exit $?
    fi
  fi
fi
exit $exit_code
