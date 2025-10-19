FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
RUN git clone https://github.com/ImageMagick/ImageMagick.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /ImageMagick/. /repo && rm -rf /ImageMagick/
RUN rm -rf /ImageMagick
RUN apt-get update -qq && apt-get install -y -qq libwebp-dev
RUN apt-get update -qq && apt-get install -y -qq libxml2-dev
RUN apt-get update -qq && apt-get install -y -qq libtiff-dev
RUN apt-get update -qq && apt-get install -y -qq libjpeg-dev
RUN apt-get update -qq && apt-get install -y -qq libopenmpi-dev
RUN apt-get update -qq && apt-get install -y -qq libjemalloc-dev
RUN apt-get update -qq && apt-get install -y -qq libtcmalloc-minimal4
RUN apt-get update -qq && apt-get install -y -qq libwmf-dev
RUN cd /repo && ./configure
RUN cd /repo && make -j4