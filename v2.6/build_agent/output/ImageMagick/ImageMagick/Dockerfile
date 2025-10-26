FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
COPY utils/repo/ImageMagick/ImageMagick/repo /repo
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout HEAD
RUN cd /repo && make -j4