#!/usr/bin/env python3

"""Parse output from mboot 'mmc part'."""
# Copyright 2024 throwaway96
# Licensed under the AGPL v3 or later
# SPDX-License-Identifier: AGPL-3.0-or-later


from __future__ import annotations
from typing import Final
from dataclasses import dataclass
import re

INPUT_FILENAME: Final[str] = "input.txt"

# where the kernel gets loaded, so it's unused at this point
BUF_ADDR: Final[int] = 0x25000000

# U-Boot is loaded around 0x27000000, so this can't be much bigger
SIZE_LIMIT: Final[int] = 0x2000000  # 32MiB (0x10000 blocks)

BLKSZ: Final[int] = 512


@dataclass
class PartInfo:
    index: int
    name: str
    start_block: int
    blocks: int

    def __init__(self, index: int, name: str, start_block: int, blocks: int) -> None:
        # XXX: should this be 1?
        if index < 0:
            raise ValueError("index can't be negative")

        self.index = index

        self.name = name

        if start_block < 0:
            raise ValueError("offset can't be negative")

        self.start_block = start_block

        if blocks < 0:
            raise ValueError("blocks can't be negative")

        self.blocks = blocks

    def size(self) -> int:
        return self.blocks * BLKSZ

    def start(self) -> int:
        return self.start_block * BLKSZ

    def end(self) -> int:
        return self.start() + self.size()

    _regex: Final[re.Pattern] = re.compile(
        r"^\s*(?P<index>\d+):\s+(?P<name>\w+)\s+(?P<size>\d+)\s@\s(?P<offset>\d+)\s+",
        re.ASCII,
    )

    def make_dump_command(self) -> str:
        filename = f"part{self.index:d}.bin"
        x_addr = f"0x{BUF_ADDR:x}"
        x_size = f"0x{self.size():x}"
        cmd_read = f"mmc read.p {x_addr} {self.name} {x_size}"
        cmd_write = f"fatwrite usb 0:1 {x_addr} {filename} {x_size}"
        return f"{cmd_read}; {cmd_write}"

    @classmethod
    def parse(cls, line: str) -> PartInfo:
        if (match := re.match(cls._regex, line)) is None:
            raise ValueError("regex doesn't match")

        d: dict[str, str] = match.groupdict()

        return cls(int(d["index"]), d["name"], int(d["offset"]), int(d["size"]))

    def __repr__(self) -> str:
        fields = f"{self.index}, '{self.name}', 0x{self.start_block:x}, 0x{self.size:x}"
        return f"{self.__class__.__name__}({fields})"


def slurp(filename: str) -> list[PartInfo]:
    parts: list[PartInfo] = []

    with open(filename, "rt", encoding="ascii") as f:
        while (line := f.readline()) != "":
            parts.append(PartInfo.parse(line))

    return parts


def print_dump_commands(parts: list[PartInfo]) -> None:
    for p in parts:
        if (size := p.size()) > SIZE_LIMIT:
            print(f"# skipping {p.name} (size 0x{size:x} > 0x{SIZE_LIMIT:x})")
            continue

        print(p.make_dump_command())


def main() -> None:
    parts: list[PartInfo] = slurp(INPUT_FILENAME)

    print_dump_commands(parts)


if __name__ == "__main__":
    main()
