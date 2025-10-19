FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
RUN git clone https://github.com/ImageMagick/ImageMagick.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /ImageMagick/. /repo && rm -rf /ImageMagick/
RUN rm -rf /ImageMagick
RUN python /home/tools/apt_download.py -p libwebp-dev
RUN python /home/tools/apt_download.py -p libxml2-dev
RUN python /home/tools/apt_download.py -p libtiff-dev
RUN python /home/tools/apt_download.py -p libjemalloc-dev
RUN python /home/tools/apt_download.py -p libgoogle-perftools-dev
RUN cd /repo && ./configure
RUN cd /repo && make