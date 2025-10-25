FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
COPY utils/repo/OpenSC/OpenSC/repo /repo
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout HEAD
RUN apt-get update -qq
RUN apt-get install -y -qq autoconf
RUN apt-get install -y -qq libtool
RUN apt-get install -y -qq automake
RUN apt-get install -y -qq pkg-config
RUN cd /repo && ./bootstrap
RUN apt-get install -y -qq libpcsclite-dev
RUN cd /repo && ./configure
RUN cd /repo && make -j4