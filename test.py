#!/usr/bin/env python3

import os
import platform
import subprocess
from pathlib import Path

size = 10**8
data = os.urandom(size)

cmdline = (
    "ip=dhcp oci.allow_no_tls dd.of=/dev/vda dd.bs=64k oci.tag=10.0.2.2:5000/test:1"
)
match system := platform.system():
    case "Darwin":
        bios = subprocess.run(
            [
                "sh",
                "-c",
                r'echo "$(brew --prefix)/Cellar/qemu/$(qemu-system-aarch64 -version | grep "QEMU emulator version" | grep -Eo "[0-9]+\.[0-9]+\.[0-9]+")/share/qemu/edk2-aarch64-code.fd"',
            ],
            check=True,
            capture_output=True,
        ).stdout.rstrip()
    case _:
        raise ValueError(f"Unsupported platform {system!r}")


Path("data").write_bytes(data)
subprocess.run(["gzip", "--force", "data"], check=True)
subprocess.run(
    ["oras", "push", "localhost:5000/test:1", "data.gz:application/octet-stream+gzip"],
    check=True,
)
subprocess.run(["qemu-img", "create", "disk.raw", "1G"])
subprocess.run(
    [
        "qemu-system-aarch64",
        "-kernel",
        "out/vmlinuz-arm64",
        "-initrd",
        "out/initramfs-arm64",
        "-machine",
        "virt",
        "-nographic",
        "-cpu",
        "cortex-a76",
        "-bios",
        bios,
        "-m",
        "1G",
        "-drive",
        "file=disk.raw",
        "-append",
        cmdline,
        "-no-reboot",
    ],
    check=True,
)

assert Path("disk.raw").read_bytes()[:size] == data
