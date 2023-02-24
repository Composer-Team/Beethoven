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

git clone -q "$prefix"Composer-Team/Composer-Hardware.git && cd Composer-Hardware && chmod u+x scripts/setup.sh && ./scripts/setup.sh && cd ..
git clone -q "$prefix"Composer-Team/Composer-Software.git && cd Composer-Software && cd ..
git clone --recursive -q "$prefix"Composer-Team/Composer-Runtime.git && cd Composer-Runtime && cd ..
git clone -q "$prefix"Composer-Team/Composer-Examples.git

echo ""
echo "==========================================================================="
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd` to your bash rc---------"
echo "-----          and add '`pwd`/bin' to your PATH variable ------------------"
echo "==========================================================================="
echo ""
