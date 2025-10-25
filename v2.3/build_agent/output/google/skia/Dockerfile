FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
COPY utils/repo/google/skia/repo /repo
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout HEAD
RUN bazel version
RUN cd /repo && git clone https://dawn.googlesource.com/dawn.git /repo/third_party/externals/dawn
RUN cd /repo/third_party/externals/dawn && git checkout 1bf0c98310db337f1cbf8ddd23a7ae41c7d80cb3
RUN cd /repo/third_party/externals/dawn && git checkout 1bf0c98310db337f1cbf8ddd23a7ae41c7d80cb3
RUN apt-get update -qq
RUN apt-get install -y -qq rustc cargo
ENV PATH=$PATH:/usr/local/cargo/bin
RUN cd /repo/bazel/external/vello && rustc --version
RUN apt-get install --reinstall -y -qq cargo
RUN cd /repo && git apply --reject /patch/patch_1.diff --allow-empty
RUN cd /repo/bazel/external/vello && cargo --version
RUN cd /repo/bazel/external/vello && cargo build