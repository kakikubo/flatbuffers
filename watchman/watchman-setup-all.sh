#!/bin/sh

cd `dirname $0`

# fixed path
for i in ~/box/*_*_asset; do
  ./watchman-setup.sh $i || exit $?
done

exit 0
