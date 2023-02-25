#!/bin/bash

branch=master
# prefix=https://www.github.com/
prefix=git@github.com:
if [ -z "${COMPOSER_ROOT-}" ]; then
	echo "You must define environment variable COMPOSER_ROOT before running setup. This is where your Composer project will live."
	exit
fi	

cp -r bin $COMPOSER_ROOT/
cd $COMPOSER_ROOT

# git clone -q "$prefix"Composer-Team/Composer-Hardware.git
git clone -q "$prefix"Composer-Team/Composer-Software.git
git clone --recursive -q "$prefix"Composer-Team/Composer-Runtime.git
git clone -q "$prefix"Composer-Team/Composer-Examples.git

echo ""
echo "==========================================================================="
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd` to your bash rc---------"
echo "-----          and add '`pwd`/bin' to your PATH variable ------------------"
echo "==========================================================================="
echo ""
