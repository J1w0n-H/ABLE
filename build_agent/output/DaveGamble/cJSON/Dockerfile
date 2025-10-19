FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
RUN git clone https://github.com/DaveGamble/cJSON.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /cJSON/. /repo && rm -rf /cJSON/
RUN rm -rf /cJSON
RUN cd /repo && mkdir build
RUN cd /repo/build && cmake ..
RUN cd /repo/build && make
RUN cd /repo/build && ctest