FROM ubuntu:latest

RUN apt-get update && apt-get install cmake g++ gcc git wget -y
# Almost certainly insecure but I'll remove this when it becomes convenient
ENV COMPOSER_ROOT=/home/ubuntu/Composer
RUN mkdir -p /home/ubuntu/Composer
ADD Composer-Software /home/ubuntu/Composer/
RUN mkdir -p /home/ubuntu/Composer/Composer-Hardware/vsim/generated-src
COPY Composer-Hardware/vsim/generated-src/composer_allocator_declaration.h /home/ubuntu/Composer/Composer-Hardware/vsim/generated-src
RUN cd /home/ubuntu/Composer && rm -rf build && mkdir build && cd build && cmake .. && make -j 8 install
RUN wget https://github.com/Xilinx/XRT/archive/refs/tags/202220.2.14.354.tar.gz && tar -xzf 202220.2.14.354.tar.gz
RUN cd XRT-202220.2.14.354 && bash ./src/runtime_src/tools/scripts/xrtdeps.sh && cd build && ./build.sh && sudo apt install --reinstall ./xrt_<version>.deb 
