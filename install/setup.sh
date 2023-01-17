#!/bin/bash

branch=master
# prefix=https://www.github.com/
prefix=git@github.com:


# Do everything in root directory
cd ..

echo "branch is $branch"

git clone -q "$prefix"ChrisKjellqvist/Composer-Hardware.git && cd Composer-Hardware && git checkout -q $branch && chmod u+x setup.sh && ./setup.sh && cd ..
git clone -q "$prefix"ChrisKjellqvist/Composer-Software.git && cd Composer-Software && git checkout -q $branch && cd ..
git clone --recursive -q "$prefix"ChrisKjellqvist/Composer_Verilator.git && cd Composer_Verilator && git checkout -q $branch && cd ..
git clone -q "$prefix"ChrisKjellqvist/Composer-Examples.git

echo ""
echo "==========================================================================="
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd` to your bash rc---------"
echo "-----          and add '`pwd`/bin' to your PATH variable ------------------"
echo "==========================================================================="
echo ""
