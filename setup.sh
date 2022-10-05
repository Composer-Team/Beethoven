#!/bin/bash

branch=master
install_yaml=0
prefix=https://www.github.com/

if test $install_yaml -eq 1
then
	echo "Installing yaml-cpp locally..."
	git clone -q https://github.com/jbeder/yaml-cpp.git
	rootdir=`pwd`
	mkdir -p "$rootdir/.local" && cd yaml-cpp && mkdir -p build && cd build && cmake .. -DCMAKE_INSTALL_PREFIX="$rootdir/.local" && make install && cd $rootdir && rm -rf yaml-cpp &> /dev/null
        echo ""
	echo "==========================================================================="
	echo "----- Make sure to add 'export YAML_DIR=$rootdir/.local' to your bashrc----"
	echo "==========================================================================="
        echo ""
fi


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
echo "install yaml is $install_yaml"


git clone -q "$prefix"ChrisKjellqvist/Composer-Hardware.git && cd Composer-Hardware && git checkout -q $branch && chmod u+x setup.sh && ./setup.sh && cd ..
git clone -q "$prefix"ChrisKjellqvist/Composer-Software.git && cd Composer-Software && git checkout -q $branch && cd ..
git clone -q "$prefix"ChrisKjellqvist/Composer_Verilator.git && cd Composer_Verilator && git checkout -q $branch && cd ..

echo ""
echo "==========================================================================="
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd`/bin to your bash rc-----"
echo "==========================================================================="
echo ""
