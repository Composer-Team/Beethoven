#!/bin/bash

branch=master
# prefix=https://www.github.com/
prefix=git@github.com:



for i in "$@"; do
	case $i in
		-b=*)
			branch="${i#*=}"
			shift
			;;
		-ssh)
			prefix=git@github.com:
			shift
			;;
		-help)
			echo "-b=<git branch name>\n\tGit branch of repositories to grab. Default is master. Usual alternative is dev\n-yaml\n\tInstall yaml-cpp prerequisite locally"
			shift
			;;
		*)
			echo "command not recognized"
			shift
			;;
	esac
done

echo "branch is $branch"

git clone -q "$prefix":ChrisKjellqvist/Composer-Hardware.git && cd Composer-Hardware && git checkout -q $branch && chmod u+x setup.sh && ./setup.sh && cd ..
git clone -q "$prefix":ChrisKjellqvist/Composer-Software.git && cd Composer-Software && git checkout -q $branch && cd ..
git clone -q "$prefix":ChrisKjellqvist/Composer_Verilator.git && cd Composer_Verilator && git checkout -q $branch && cd ..
git clone -q "$prefix":ChrisKjellqvist/Composer-Examples.git

echo ""
echo "==========================================================================="
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd` to your bash rc---------"
echo "-----          and add '`pwd`/bin' to your PATH variable ------------------"
echo "==========================================================================="
echo ""
