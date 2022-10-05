#!/bin/bash

branch=master
install_yaml=0

for i in "$@"; do
	case $i in
		-b=*)
			branch="${i#*=}"
			shift
			;;
		-yaml)
			install_yaml=1
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
echo "install yaml is $install_yaml"


git submodule update --init Composer-Hardware &> /dev/null
cd Composer-Hardware && chmod u+x setup.sh && ./setup.sh && cd .. &> /dev/null
git submodule update --init &> /dev/null

if test $install_yaml -eq 1
then
	echo "Installing yaml-cpp locally..."
	git clone https://github.com/jbeder/yaml-cpp.git &> /dev/null
	rootdir=`pwd`
	echo "$rootdir"
	mkdir $(rootdir)".local" && cd yaml-cpp && mkdir build && cd build && cmake .. -q -DCMAKE_INSTALL_PREFIX="$rootdir/.local" && make install && cd $rootdir
	echo "==========================================================================="
	echo "----- Make sure to add 'export YAML_DIR=$rootdir/.local' to your bashrc----"
	echo "==========================================================================="
fi

if test $install_yaml -eq 0
then
	echo "==========================================================================="
fi
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd`/bin to your bash rc-----"
echo "==========================================================================="

