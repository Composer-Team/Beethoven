#!/bin/bash

git clone https://github.com/verilator/verilator.git
cd verilator || exit
git checkout v4.226-66-gf96454adc
autoconf

for i in "$@"; do
  case $i in
    -local)
      INSTALL_DIR="$(pwd)/../"
      ./configure --prefix="$INSTALL_DIR"

      make -j8
      make install

      echo "--------------------------------------------------------------------------"
      echo "------ Add the following lines to your .bashrc ---------------------------"
      echo "export PATH=\$PATH:$INSTALL_DIR/bin"
      echo "export LD_RUN_PATH=\$LD_RUN_PATH:$INSTALL_DIR/lib"
      echo "export LD_LIBRARY_PATH=\$LD_LIBRARY_PATH:$INSTALL_DIR/lib"
      exit
      ;;
    -root)
      ./configure
      make -j8
      make install
      exit
      ;;
    *)
      echo "Please provide one of the following flags to determine where to install"
      echo "-root     Install globally"
      echo "-local    Install in local directory. This requires modifications to path variables."
      exit
      ;;
  esac
done


echo "Please provide one of the following flags to determine where to install"
echo "-root     Install globally"
echo "-local    Install in local directory. This requires modifications to path variables."
