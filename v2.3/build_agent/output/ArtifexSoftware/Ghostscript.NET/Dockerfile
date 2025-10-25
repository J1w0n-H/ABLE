FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
COPY utils/repo/ArtifexSoftware/Ghostscript.NET/repo /repo
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout HEAD
RUN apt-get update -qq
RUN wget https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb
RUN dpkg -i packages-microsoft-prod.deb
RUN apt-get update -qq
RUN apt-get install -y -qq dotnet-sdk-6.0
RUN cd /repo/Ghostscript.NET && dotnet build
RUN cd /repo && git apply --reject /patch/patch_1.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_1.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_2.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_2.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_3.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_3.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_4.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_4.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_5.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_5.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_6.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_6.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_7.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_7.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_8.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_8.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_9.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_9.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_10.diff --allow-empty
RUN cd /repo/Ghostscript.NET && dotnet build