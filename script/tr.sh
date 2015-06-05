#!/bin/sh

cat $1 | tr '+' '\n' > $1.tmp || exit $?
mv $1.tmp $1
exit $?
