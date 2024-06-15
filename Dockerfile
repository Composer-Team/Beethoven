FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update
# Use this to fully build & run
# RUN apt-get install cmake g++ gcc git wget python3 valgrind gdb build-essential verilator  -y
# This should be fine for building and ensuring compile
RUN apt-get install cmake g++ wget build-essential -y
ENV COMPOSER_ROOT=/home/ubuntu/Composer
ADD ./Composer-Software/ /home/ubuntu/Composer/Composer-Software
RUN cd /home/ubuntu/Composer/Composer-Software/ && rm -rf build && mkdir -p build && cd build && cmake .. && make install
ADD ./Composer-Hardware/vsim/generated-src/ /home/ubuntu/Composer/Composer-Hardware/vsim/generated-src
