#!/bin/bash

for dir in $*; do
  echo "strip PNG in '$dir'"
  for i in `find $dir -name '*.png'`; do
    echo $i
    mogrify $i || exit $?
  done
done
