FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
RUN git clone https://github.com/leethomason/tinyxml2.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /tinyxml2/. /repo && rm -rf /tinyxml2/
RUN rm -rf /tinyxml2
RUN cd /src && mkdir -p /repo/build
RUN cd /repo/build && cmake ..
RUN cd /repo/build && make
RUN cd /repo/build && ctest