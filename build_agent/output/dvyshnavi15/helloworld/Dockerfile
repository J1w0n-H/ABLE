FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
RUN git clone https://github.com/dvyshnavi15/helloworld.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /helloworld/. /repo && rm -rf /helloworld/
RUN rm -rf /helloworld
RUN cd /src && gcc /repo/hello.c -o /repo/hello
RUN cd /src && /repo/hello