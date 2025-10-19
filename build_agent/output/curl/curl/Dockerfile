FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
COPY search_patch /search_patch
# C build tools already included in base-builder
RUN git clone https://github.com/curl/curl.git
RUN mkdir /repo
RUN git config --global --add safe.directory /repo
RUN cp -r /curl/. /repo && rm -rf /curl/
RUN rm -rf /curl
RUN python /home/tools/apt_download.py -p zlib1g-dev
RUN python /home/tools/apt_download.py -p libbrotli-dev
RUN python /home/tools/apt_download.py -p libzstd-dev
RUN python /home/tools/apt_download.py -p libpsl-dev
RUN python /home/tools/apt_download.py -p libuv1-dev
RUN python /home/tools/apt_download.py -p libpthread-stubs0-dev
RUN cd /src && apt-cache search libnsl-dev libsockets-dev libwatt-dev libnetwork-dev libngtcp2-dev libnghttp3-dev libquiche-dev
RUN cd /src && apt-cache search libnghttp3-dev libngtcp2-dev libquiche-dev
RUN cd /src && # Checking the official repositories for installation instructions curl -s https://github.com/ngtcp2/ngtcp2 | grep -i "installation" curl -s https://github.com/ngtcp2/nghttp3 | grep -i "installation" curl -s https://github.com/cloudflare/quiche | grep -i "installation"
RUN cd /src && curl -s https://raw.githubusercontent.com/ngtcp2/ngtcp2/master/README.md
RUN cd /src && curl -s https://raw.githubusercontent.com/ngtcp2/ngtcp2/master/README.md
RUN python /home/tools/apt_download.py -p libgnutls28-dev
RUN python /home/tools/apt_download.py -p libc-ares-dev
RUN python /home/tools/apt_download.py -p librtmp-dev
RUN cd /src && mkdir -p /repo/build
RUN cd /repo/build && cmake ..
RUN cd /repo/build && make