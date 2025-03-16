ARG ALPINE_VERSION=3.21.3

FROM alpine AS linux-src
ARG LINUX_VERSION

RUN apk add --no-cache wget

RUN <<EOF
set -eu
wget https://cdn.kernel.org/pub/linux/kernel/v${LINUX_VERSION%%.*}.x/linux-${LINUX_VERSION}.tar.xz
tar xf linux-*.tar.xz
rm linux-*.tar.xz
mv linux-* /linux
EOF

FROM ubuntu:noble AS vmlinuz
ARG BUILD_TIMESTAMP

RUN <<EOF
set -e
apt-get update
apt-get install -y\
 bc\
 bison\
 build-essential\
 flex\
 libelf-dev\
 libssl-dev\
 python3
EOF

COPY --from=linux-src linux /linux-src
WORKDIR /linux-src

RUN make defconfig
RUN make KBUILD_BUILD_HOST=localhost KBUILD_BUILD_TIMESTAMP="${BUILD_TIMESTAMP?}" --jobs=$(nproc)

RUN mv $(find arch/*/boot/*Image -type f) /vmlinuz-$(dpkg --print-architecture)
WORKDIR /

FROM alpine AS busybox-src
ARG BUSYBOX_VERSION

RUN apk add --no-cache bzip2 tar wget

RUN <<EOF
set -eu
wget https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2
bzip2 --decompress busybox-*.tar.bz2
tar xf busybox-*.tar
rm busybox-*.tar
mv busybox-* /busybox
EOF

FROM ubuntu:noble AS busybox

RUN apt-get update && apt-get install --yes build-essential

COPY --from=busybox-src busybox /busybox-src
WORKDIR /busybox-src

RUN make defconfig
RUN sed --in-place '/# CONFIG_STATIC is not set/c\CONFIG_STATIC=y' .config
# https://lists.busybox.net/pipermail/busybox-cvs/2024-January/041752.html
RUN sed --in-place '/CONFIG_TC=y/c\# CONFIG_TC is not set' .config
RUN make KCONFIG_NOTIMESTAMP=1 --jobs=$(nproc)
RUN cp busybox /busybox

FROM debian AS oras
ARG ORAS_VERSION

RUN apt-get update && apt-get install --yes tar wget

RUN <<EOF
set -eu
wget https://github.com/oras-project/oras/releases/download/v${ORAS_VERSION}/oras_${ORAS_VERSION}_linux_$(dpkg --print-architecture).tar.gz
tar xzf oras_*_linux_*.tar.gz
chmod +x oras
EOF

FROM debian AS jq
ARG JQ_VERSION

RUN apt-get update && apt-get install --yes wget

RUN <<EOF
set -eu
wget https://github.com/jqlang/jq/releases/download/jq-${JQ_VERSION}/jq-linux-$(dpkg --print-architecture)
mv jq-linux-* jq
chmod +x jq
EOF

FROM alpine:$ALPINE_VERSION AS ca-certificates

RUN cp /etc/ssl/certs/ca-certificates.crt ./

FROM alpine AS fs

WORKDIR /fs

COPY src/init .
COPY src/ocidd bin/
RUN chmod 755 init bin/ocidd

COPY --from=busybox busybox bin/
COPY --from=oras oras bin/
COPY --from=jq jq bin/
COPY --from=ca-certificates ca-certificates.crt etc/ssl/certs/

FROM ubuntu AS initramfs
ARG MTIME

RUN apt-get update && apt-get install --yes cpio gzip

COPY --from=fs fs fs/

# NOTE: mtime cannot be set in another stage
RUN find fs -exec touch -d ${MTIME?} {} +
RUN cd fs && find . | sort | cpio --reproducible --format=newc --create | gzip > /initramfs-$(dpkg --print-architecture).gz
