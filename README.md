# ocidd

[ocidd](src/ocidd) is a program that fetches a raw (gzipped) blob from an OCI registry and writes it to some volume.
This can help to simplify system installation and to avoid reliance on certain infrastructure (virtualization, storage network, ..) or specialized installers (Cloud-init, Kickstart, ..).

Bundled in an appropriate initial RAM-disk (initrd/initramfs), `ocidd` can be used, for example, for a fully automated installation of bare-metal hosts from a PXE.
We provide prebuilt vmlinuz+initramfs (`x86_64`, `arm64`).

## Usage

For automatic installation, the arguments `dd.of`, `dd.bs`, as well as either one of `oci.tag` and `oci.blob` must be supplied to `ocidd`.
Missing parameters can be supplied interactively.

[init](src/init) will forward the kernel parameters as arguments to `ocidd`.
For automatic network setup, the parameter `ip` (e.g. `ip=dhcp`) should be used (this is a [kernel feature](https://www.kernel.org/doc/Documentation/admin-guide/nfs/nfsroot.rst) that is available in a default kernel build but is notably excluded from most Linux distributions).
</br>
If `ocidd` fails (e.g. due to missing network or an I/O error), `init` will launch an emergency shell.
Otherwise, it will initiate a reboot.
                                                                                               
| Parameter          | Description                                                                                                                          | Example                                                                                                              |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| `oci.tag`          | OCI tag to fetch. There must be exactly one layer of media type `application/octet-stream+gzip`. Mutually exclusive with `oci.blob`. | `oci.tag=registry.example.com/repos/mydisk:v0`                                                                       |
| `oci.blob`         | OCI blob to fetch. Must be a gzip-compressed raw disk image. Mutually exclusive with `oci.tag`.                                       | `oci.blob=registry.example.com/repos/mydisk@sha256:243786d4bef167ff79122d052ded386cbac007e71bdb9e15d6ffbf31b6dbe54d` |
| `oci.allow_no_tls` | If set, fetching manifests/blobs without TLS is allowed. Corresponds to oras' `--plain-http`.                                        |                                                                                                                      |
| `dd.of`            | Disk to write to.                                                                                                                    | `dd.of=/dev/sda`                                                                                                     |
| `dd.bs`            | Block size to during write.                                                                                                          | `dd.bs=64k`                                                                                                          |
| `wait`             | If set, confirmation will be prompted before installing.                                                                             |                                                                                                                      |

## Building

The following [compose services](compose.yaml) are provided:

- `initramfs` for building a ram disk containing [ocidd](src/ocidd), an appropriate [init script](src/init), as well as the required tools [busybox](https://busybox.net/), [oras](https://oras.land/), and [jq](https://jqlang.org/), and a CA-bundle taken from [Alpine](https://hub.docker.com/_/alpine).
- `vmlinuz` for building a linux kernel with the default configuration.
- `registry` for running a [simple OCI registry](https://hub.docker.com/_/registry) (without TLS) for testing purposes.

To ensure builds are reproducible, dates need to be provided for the kernel version/the mtime of files in the initramfs:

```sh
echo "KERNEL_BUILD_TIMESTAMP='$(date)'" > .env
echo "FS_MTIME='$(date -u -Iseconds)'" >> .env
```

## Testing

See [test.py](test.py) for testing using [QEMU](https://www.qemu.org/).
