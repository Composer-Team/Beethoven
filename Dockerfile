FROM ubuntu:20.04

ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update
RUN apt-get install cmake g++ gcc git wget python3 -y
# Almost certainly insecure but I'll remove this when it becomes convenient
ENV COMPOSER_ROOT=/home/ubuntu/Composer
RUN mkdir -p /home/ubuntu/Composer
ADD Composer-Software /home/ubuntu/Composer/
RUN mkdir -p /home/ubuntu/Composer/Composer-Hardware/vsim/generated-src
COPY Composer-Hardware/vsim/generated-src/composer_allocator_declaration.h /home/ubuntu/Composer/Composer-Hardware/vsim/generated-src
RUN cd /home/ubuntu/Composer && rm -rf build && mkdir build && cd build && cmake .. && make -j 8 install
