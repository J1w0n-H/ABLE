FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
COPY search_patch /search_patch
# C build tools already included in base-builder
RUN git clone https://github.com/nothings/stb.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /stb/. /repo && rm -rf /stb/
RUN rm -rf /stb
RUN cd /repo && git apply --reject /patch/patch_1.diff --allow-empty
RUN cd /repo/tests && make