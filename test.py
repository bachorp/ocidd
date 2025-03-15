#!/usr/bin/env python3

import hashlib
import os
import platform
import subprocess
from pathlib import Path

arch = os.environ.get(
    "ARCH",
    subprocess.run(["arch"], check=True, capture_output=True).stdout.decode().rstrip(),
)
blob = bool(os.environ.get("BLOB"))
data_bytes = int(os.environ.get("DATA_BYTES", 10**8))
disk_size = os.environ.get("DISK_SIZE", "1G")
block_size = os.environ.get("BLOCK_SIZE", "64k")

cmdline = [
    "ip=dhcp",
    "oci.allow_no_tls",
    f"dd.bs={block_size}",
]

match arch:
    case "x86_64":
        base_cmd = [
            "qemu-system-x86_64",
            "-kernel",
            "out/vmlinuz-amd64",
            "-initrd",
            "out/initramfs-amd64",
        ]
        cmdline += [
            "dd.of=/dev/sda",
            "console=ttyS0",
        ]
    case "aarch64":
        match system := platform.system():
            case "Darwin":
                bios = (
                    subprocess.run(
                        [
                            "sh",
                            "-c",
                            r'echo "$(brew --prefix)/Cellar/qemu/$(qemu-system-aarch64 -version | grep "QEMU emulator version" | grep -Eo "[0-9]+\.[0-9]+\.[0-9]+")/share/qemu/edk2-aarch64-code.fd"',
                        ],
                        check=True,
                        capture_output=True,
                    )
                    .stdout.decode()
                    .rstrip()
                )
            case "Linux":
                bios = "/usr/share/edk2/aarch64/QEMU_EFI.fd"
            case _:
                raise ValueError(f"Unsupported platform {system!r}")
        base_cmd = [
            "qemu-system-aarch64",
            "-kernel",
            "out/vmlinuz-arm64",
            "-initrd",
            "out/initramfs-arm64",
            "-machine",
            "virt",
            "-bios",
            bios,
            "-cpu",
            "cortex-a76",
            "-m",
            "1G",
        ]
        cmdline += ["dd.of=/dev/vda"]
    case _:
        raise ValueError(f"Unsupported architecture {arch!r}")

data = os.urandom(data_bytes)
Path("data").write_bytes(data)
subprocess.run(["gzip", "--force", "data"], check=True)

if blob:
    subprocess.run(
        [
            "oras",
            "blob",
            "push",
            f"localhost:5000/test",
            "data.gz",
        ],
        check=True,
    )
    cmdline += [
        f"oci.blob=10.0.2.2:5000/test@sha256:{hashlib.sha256(Path("data.gz").read_bytes()).hexdigest()}"
    ]
else:
    subprocess.run(
        [
            "oras",
            "push",
            "localhost:5000/test:1",
            "data.gz:application/octet-stream+gzip",
        ],
        check=True,
    )
    cmdline += ["oci.tag=10.0.2.2:5000/test:1"]

subprocess.run(["qemu-img", "create", "disk.raw", disk_size], check=True)
subprocess.run(
    base_cmd
    + [
        "-nographic",
        "-drive",
        "file=disk.raw,format=raw",
        "-append",
        " ".join(cmdline),
        "-no-reboot",
    ],
    check=True,
)

assert Path("disk.raw").read_bytes()[:data_bytes] == data
