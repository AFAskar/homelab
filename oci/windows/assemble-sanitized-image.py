#!/usr/bin/env python3
"""Replace one matching GPT Windows partition in a NEW sparse raw disk copy."""
import argparse
import os
import struct
import uuid
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('original_raw', type=Path)
p.add_argument('sanitized_ntfs', type=Path)
p.add_argument('output_raw', type=Path)
a = p.parse_args()
os.umask(0o077)
size = a.original_raw.stat().st_size
partition_size = a.sanitized_ntfs.stat().st_size
with a.original_raw.open('rb') as source, a.sanitized_ntfs.open('rb') as partition:
    source.seek(512)
    header = source.read(92)
    if header[:8] != b'EFI PART':
        raise SystemExit('Expected the discovered 512-byte-sector GPT raw disk.')
    table_lba, count, entry_size = struct.unpack_from('<QII', header, 72)
    if not 0 < count <= 1024 or not 128 <= entry_size <= 4096:
        raise SystemExit('Invalid GPT entry layout.')
    source.seek(table_lba * 512)
    matches = []
    for _ in range(count):
        entry = source.read(entry_size)
        if len(entry) != entry_size:
            raise SystemExit('Truncated GPT table.')
        if uuid.UUID(bytes_le=entry[:16]) == uuid.UUID('ebd0a0a2-b9e5-4433-87c0-68b6b72699c7'):
            first, last = struct.unpack_from('<QQ', entry, 32)
            if (last - first + 1) * 512 == partition_size:
                matches.append((first * 512, (last + 1) * 512))
    if len(matches) != 1 or partition.read(11)[3:11] != b'NTFS    ':
        raise SystemExit('Require exactly one size-matching Windows data partition and an NTFS copy.')
    start, end = matches[0]
    if not 0 < start < end < size:
        raise SystemExit('Partition bounds exceed the source disk.')
    zeros = bytes(8 * 1024 * 1024)
    with a.output_raw.open('xb') as output:
        output.truncate(size)
        def copy(stream, source_offset, output_offset, length):
            stream.seek(source_offset)
            output.seek(output_offset)
            while length:
                data = stream.read(min(len(zeros), length))
                if not data:
                    raise RuntimeError('Unexpected end of input; discard the incomplete output copy.')
                if data == zeros[:len(data)]:
                    output.seek(len(data), 1)
                else:
                    output.write(data)
                length -= len(data)
        copy(source, 0, 0, start)
        copy(partition, 0, start, partition_size)
        copy(source, end, end, size - end)
print('Created sparse disk copy; GPT/EFI/recovery preserved, sanitized NTFS substituted.')
