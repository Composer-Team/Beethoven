#!/bin/bash

branch=master
# prefix=https://www.github.com/
prefix=git@github.com:



for i in "$@"; do
	case $i in
	  -aws)
	    git clone https://github.com/aws/aws-fpga.git
	    cd aws-fpga || exit
	    sudo yum groupinstall "Development tools"
	    sudo yum install kernel kernel-devel
	    sudo systemctl stop mpd || true
	    sudo yum remove -y xrt xrt-aws || true
	    source sdk_setup.sh
	    cd sdk/linux_kernel_drivers/xdma || exit
	    make && sudo make install
	    echo "If the kernel module is running (and working), you should see some files below:"
	    ls /dev/xdma
	    echo "If there's nothing printed out above, try restarting the F1 instance."
	    ;;
	  -awsclone)
	    git clone https://github.com/aws/aws-fpga.git
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

git clone -q "$prefix"Composer-Team/Composer-Hardware.git && cd Composer-Hardware && git checkout -q $branch && chmod u+x scripts/setup.sh && ./scripts/setup.sh && cd ..
git clone -q "$prefix"Composer-Team/Composer-Software.git && cd Composer-Software && git checkout -q $branch && cd ..
git clone --recursive -q "$prefix"Composer-Team/Composer-Runtime.git && cd Composer-Runtime && git checkout -q $branch && cd ..
git clone -q "$prefix"Composer-Team/Composer-Examples.git

echo ""
echo "==========================================================================="
echo "----- Make sure to add 'export COMPOSER_ROOT=`pwd` to your bash rc---------"
echo "-----          and add '`pwd`/bin' to your PATH variable ------------------"
echo "==========================================================================="
echo ""
