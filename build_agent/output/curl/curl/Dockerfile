FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
COPY search_patch /search_patch
# C build tools already included in base-builder
RUN git clone https://github.com/curl/curl.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /curl/. /repo && rm -rf /curl/
RUN rm -rf /curl
RUN python /home/tools/apt_download.py -p libssl-dev
RUN python /home/tools/apt_download.py -p libmbedtls-dev
RUN python /home/tools/apt_download.py -p libwolfssl-dev
RUN python /home/tools/apt_download.py -p libgnutls28-dev
RUN python /home/tools/apt_download.py -p libnghttp2-dev
RUN python /home/tools/apt_download.py -p libldap2-dev
RUN python /home/tools/apt_download.py -p libidn2-0-dev
RUN python /home/tools/apt_download.py -p libpsl-dev
RUN python /home/tools/apt_download.py -p libssh2-1-dev
RUN python /home/tools/apt_download.py -p libssh-dev
RUN python /home/tools/apt_download.py -p libgsasl7-dev
RUN python /home/tools/apt_download.py -p libuv1-dev
RUN python /home/tools/apt_download.py -p librtmp-dev
RUN cd /src && apt-cache search c-ares
RUN cd /src && mkdir /repo/build
RUN cd /repo/build && cmake ..
RUN python /home/tools/apt_download.py -p libc-ares-dev
RUN python /home/tools/apt_download.py -p libssl-dev
RUN python /home/tools/apt_download.py -p libmbedtls-dev
RUN python /home/tools/apt_download.py -p libwolfssl-dev
RUN python /home/tools/apt_download.py -p libgnutls28-dev
RUN python /home/tools/apt_download.py -p libnghttp2-dev
RUN python /home/tools/apt_download.py -p libldap2-dev
RUN python /home/tools/apt_download.py -p libidn2-0-dev
RUN python /home/tools/apt_download.py -p libpsl-dev
RUN python /home/tools/apt_download.py -p libssh2-1-dev
RUN python /home/tools/apt_download.py -p libssh-dev
RUN python /home/tools/apt_download.py -p libgsasl7-dev
RUN python /home/tools/apt_download.py -p libuv1-dev
RUN python /home/tools/apt_download.py -p librtmp-dev
RUN cd /repo/build && cmake ..
RUN python /home/tools/apt_download.py -p zlib1g-dev
RUN python /home/tools/apt_download.py -p libbrotli-dev
RUN python /home/tools/apt_download.py -p libzstd-dev
RUN python /home/tools/apt_download.py -p libpthread-stubs0-dev