FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
RUN git clone https://github.com/test/hello-world-c.git
RUN mkdir /repo
RUN cp -r /hello-world-c/. /repo && rm -rf /hello-world-c/
RUN cd /repo && git checkout ae31c20fa4fdfcc1d3899f5f6fc8c50594b548f1