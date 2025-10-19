FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
RUN git clone https://github.com/curl/curl.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /curl/. /repo && rm -rf /curl/
RUN rm -rf /curl
RUN cd /repo && git checkout 7e12139
RUN apt-get update -qq && apt-get install -y -qq autoconf
RUN apt-get update -qq && apt-get install -y -qq automake
RUN apt-get update -qq && apt-get install -y -qq libtool
RUN apt-get update -qq && apt-get install -y -qq pkg-config
RUN cd /repo && autoreconf -fi
RUN apt-get update -qq && apt-get install -y -qq libssl-dev
RUN cd /repo && autoreconf -fi
RUN mkdir -p /repo/build
RUN apt-get update -qq && apt-get install -y -qq libpsl-dev
RUN apt-get update -qq && apt-get install -y -qq libidn2-dev
RUN apt-get update -qq && apt-get install -y -qq libnghttp2-dev
RUN apt-get update -qq && apt-get install -y -qq libzstd-dev
RUN apt-get update -qq && apt-get install -y -qq libbrotli-dev
RUN apt-get update -qq && apt-get install -y -qq zlib1g-dev
RUN cd /repo/build && cmake .. -DCMAKE_BUILD_TYPE=Release
RUN cd /repo/build && make -j4