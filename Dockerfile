FROM ubuntu:22.04

ENV TZ=Europe/Berlin
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

USER root
RUN apt-get update
RUN apt-get -y -qq install software-properties-common
RUN add-apt-repository ppa:ubuntu-toolchain-r/test
RUN apt-get update --fix-missing && apt-get -y -qq install autoconf automake autotools-dev build-essential clang-13 clang-tools-13 cmake cvc4 \
                           gcc-10 git mpich libboost-dev libboost-context-dev libcairo2 libdw-dev \
                           libelf-dev libevent-dev libllvm13 libncurses5 libunwind-dev libtinfo-dev \
                           libtool libxml2-dev libz3-dev llvm-13 llvm-13-dev lsof openjdk-18-jdk-headless psmisc \
                           python3-jinja2 python3-pip quilt valgrind wget z3 zlib1g-dev && \
    apt-get autoremove -yq && \
    apt-get clean -yq

# RUN pip3 install drawSvg
COPY . /MBI
