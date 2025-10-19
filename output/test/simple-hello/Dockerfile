FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
RUN git clone https://github.com/test/simple-hello.git
RUN mkdir /repo
RUN cp -r /simple-hello/. /repo && rm -rf /simple-hello/
RUN cd /repo && git checkout a3f4ee83a09ff8878e687d9aa5155945666d1947