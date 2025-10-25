FROM gcr.io/oss-fuzz-base/base-builder
WORKDIR /
# C build tools already included in base-builder
COPY utils/repo/FFmpeg/FFmpeg/repo /repo
RUN git config --global --add safe.directory /repo
RUN cd /repo && git checkout HEAD
RUN apt-get update -qq
RUN apt-get install -y -qq build-essential autoconf
RUN apt-get install -y -qq clang
ENV CC=clang
ENV CXX=clang++
RUN apt-get install -y -qq gcc-10 g++-10
RUN cd /repo && update-alternatives --install /usr/bin/gcc gcc /usr/bin/gcc-10 10
RUN cd /repo && update-alternatives --install /usr/bin/g++ g++ /usr/bin/g++-10 10
ENV CC=gcc-10
ENV CXX=g++-10
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
RUN cd /repo && git apply -R --reject /patch/patch_10.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_11.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_11.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_12.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_12.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_13.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_13.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_14.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_14.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_15.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_15.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_16.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_16.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_17.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_17.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_18.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_18.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_19.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_19.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_20.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_20.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_21.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_21.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_22.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_22.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_23.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_23.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_24.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_24.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_25.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_25.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_26.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_26.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_27.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_27.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_28.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_28.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_29.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_29.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_30.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_30.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_31.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_31.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_32.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_32.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_33.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_33.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_34.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_34.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_35.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_35.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_36.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_36.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_37.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_37.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_38.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_38.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_39.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_39.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_40.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_40.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_41.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_41.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_42.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_42.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_43.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_43.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_44.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_44.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_45.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_45.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_46.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_46.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_47.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_47.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_48.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_48.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_49.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_49.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_50.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_50.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_51.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_51.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_52.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_52.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_53.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_53.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_54.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_54.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_55.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_55.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_56.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_56.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_57.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_57.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_58.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_58.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_59.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_59.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_60.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_60.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_61.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_61.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_62.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_62.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_63.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_63.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_64.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_64.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_65.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_65.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_66.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_66.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_67.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_67.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_68.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_68.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_69.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_69.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_70.diff --allow-empty
RUN cd /repo && git apply -R --reject /patch/patch_70.diff --allow-empty
RUN cd /repo && git apply --reject /patch/patch_71.diff --allow-empty