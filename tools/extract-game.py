#!/usr/bin/env python3
"""Extract the game files of an Xbox 360 disc image in one pass, without the image on disk.

The image comes from a .iso, from a .7z holding one (7-Zip decodes it to a pipe),
or with --salvage from a .7z whose download stopped early: its LZMA2 stream is
decoded as far as it goes, and the files it does not reach are listed as missing.
A disc image is about 7 GB, which a Mac with little free space may not have
beside the extracted files.

The XDVDFS game partition is read as the image streams past: the volume
descriptor gives the root directory table, each directory table read gives the
files and tables it lists, and every file is written as its sectors go by. The
entries a table lists before itself (Broken Bond keeps default.xex there) are
read in another pass.
"""
import argparse
import heapq
import itertools
import lzma
from pathlib import Path
import shutil
import struct
import subprocess
import sys

SECTOR = 2048
MAGIC = b'MICROSOFT*XBOX*MEDIA'
# Game partition offsets: plain XISO, XGD3 and XGD2 full-disc images, XGD1.
PARTITIONS = (0, 0x2080000, 0xFD90000, 0x18300000)
CHUNK = 4 << 20
RESERVED = {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}


def lzma2_stream(archive):
    """The decoded stream of a single-file 7z whose LZMA2 data starts after its 32-byte header."""
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_RAW,
                                    filters=[{'id': lzma.FILTER_LZMA2, 'dict_size': 1536 << 20}])
    with archive.open('rb') as stream:
        if stream.read(6) != b"7z\xbc\xaf'\x1c":
            raise ValueError(f'Not a 7z archive: {archive}')
        stream.seek(32)
        while not decoder.eof:
            data = stream.read(CHUNK)
            if not data:
                return
            try:
                yield decoder.decompress(data)
            except lzma.LZMAError:
                return  # The download stopped mid-block.


def piped_stream(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE)
    try:
        while data := process.stdout.read(CHUNK):
            yield data
    finally:
        process.stdout.close()
        if process.wait():
            raise ValueError(f'{command[0]} failed with status {process.returncode}')


def file_stream(path):
    with path.open('rb') as stream:
        while data := stream.read(CHUNK):
            yield data


def check_name(name):
    if (not name or any(c in name for c in '/\\:<>"|?*') or any(ord(c) < 32 for c in name) or
            name.rstrip(' .') != name or name.split('.')[0].upper() in RESERVED or name in ('.', '..')):
        raise ValueError(f'Invalid file name in disc image: {name!r}')


def directory_entries(table):
    """(name, sector, size, is_directory) of one directory table (a binary tree of entries)."""
    pending, seen = [0], set()
    while pending:
        offset = pending.pop()
        if offset in seen or offset + 14 > len(table):
            continue
        seen.add(offset)
        left, right, start, length, attributes, name_length = struct.unpack_from('<HHIIBB', table, offset)
        if left == 0xFFFF and right == 0xFFFF:
            continue  # Sector padding.
        name = table[offset + 14:offset + 14 + name_length].decode('ascii', 'strict')
        check_name(name)
        yield name, start, length, bool(attributes & 0x10)
        for child in (left, right):
            if child and child != 0xFFFF:
                pending.append(child * 4)


class Region:
    def __init__(self, start, size, kind, path):
        self.start, self.end, self.kind, self.path = start, start + size, kind, path
        self.done = 0
        self.data = bytearray() if kind != 'file' else None
        self.sink = None


def extract_pass(chunks, output, resume, seeds, partition):
    """One pass over the image: the regions of `seeds` (the volume descriptors
    when the partition is not known yet) and every one the tables read give.

    Returns what it wrote, how far the image went, the regions past its end, the
    regions behind the stream when a table listed them (for another pass) and
    the partition.
    """
    order = itertools.count()
    pending = []  # (start, order, region): regions the stream has not reached.
    if partition is None:
        for offset in PARTITIONS:
            seeds = [*seeds, Region(offset + 32 * SECTOR, 28, 'volume', offset)]
    for region in seeds:
        heapq.heappush(pending, (region.start, next(order), region))
    active, missed = [], []
    written = 0
    position = 0

    def add(region):
        if region.end == region.start and region.kind == 'file':
            region.path.parent.mkdir(parents=True, exist_ok=True)
            region.path.touch()
            return
        if region.end == region.start and region.kind == 'directory':
            region.path.mkdir(parents=True, exist_ok=True)
            return
        heapq.heappush(pending, (region.start, next(order), region))

    def finish(region):
        nonlocal partition, written
        if region.kind == 'volume':
            if partition is None and bytes(region.data[:20]) == MAGIC:
                partition = region.path
                root_sector, root_size = struct.unpack_from('<II', region.data, 20)
                add(Region(partition + root_sector * SECTOR, root_size, 'directory', output))
        elif region.kind == 'directory':
            region.path.mkdir(parents=True, exist_ok=True)
            for name, start, length, is_directory in directory_entries(bytes(region.data)):
                add(Region(partition + start * SECTOR, length, 'directory' if is_directory else 'file',
                           region.path / name))
        else:
            if region.sink:
                region.sink.close()
            written += region.end - region.start

    for chunk in chunks:
        begin, end = position, position + len(chunk)
        position = end
        changed = True
        while changed:
            changed = False
            while pending and pending[0][0] < end:
                region = heapq.heappop(pending)[2]
                if region.kind == 'volume' and partition is not None:
                    continue
                if region.start < begin:
                    # Behind the stream: a table listed it after its sectors went by.
                    missed.append(Region(region.start, region.end - region.start, region.kind, region.path))
                    continue
                if region.kind == 'file':
                    region.path.parent.mkdir(parents=True, exist_ok=True)
                    # A file an earlier extraction left whole is read past, not written again.
                    if not (resume and region.path.is_file() and
                            region.path.stat().st_size == region.end - region.start):
                        region.sink = region.path.open('wb')
                active.append(region)
            for region in list(active):
                low, high = max(region.start + region.done, begin), min(region.end, end)
                if low < high:
                    piece = chunk[low - begin:high - begin]
                    if region.sink:
                        region.sink.write(piece)
                    elif region.kind != 'file':
                        region.data += piece
                    region.done += high - low
                if region.start + region.done >= region.end:
                    active.remove(region)
                    finish(region)
                    changed = True
    # What the stream never reached: a file whose sectors lie past a download that stopped.
    truncated = []
    for region in active + [entry[2] for entry in pending]:
        if region.kind == 'volume':
            continue
        if region.sink:
            region.sink.close()
            region.path.unlink(missing_ok=True)
        truncated.append(region)
    return written, position, truncated, missed, partition


def extract(open_chunks, output, resume=False):
    """Every file of the image, in as many passes as the tables' order needs."""
    written, partition, seeds, read = 0, None, [], 0
    for _ in range(8):
        done, read, truncated, missed, partition = extract_pass(open_chunks(), output, resume, seeds, partition)
        written += done
        if partition is None:
            raise ValueError('Not an Xbox 360 disc image (no XDVDFS volume found)')
        if not missed or truncated or (seeds and len(missed) >= len(seeds) and
                                       {r.start for r in missed} == {r.start for r in seeds}):
            return written, read, truncated + missed
        print(f'{len(missed)} entries come before the table that lists them: another pass', flush=True)
        seeds = missed
    return written, read, missed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='the disc image (.iso) or a .7z holding it')
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--salvage', action='store_true',
                        help='decode an incomplete .7z as far as it goes and list the files it lacks')
    parser.add_argument('--resume', action='store_true',
                        help='keep the files of an earlier extraction that are already whole')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.resume:
        parser.error(f'Output already exists: {args.output} (--resume keeps its whole files)')
    if args.source.suffix.lower() == '.7z' and args.salvage:
        open_chunks = lambda: lzma2_stream(args.source)
    elif args.source.suffix.lower() == '.7z':
        tool = shutil.which('7zz') or shutil.which('7z')
        if not tool:
            parser.error('Extracting a .7z needs 7-Zip: brew install sevenzip')
        # The disc image alone (an archive may hold a readme beside it).
        open_chunks = lambda: piped_stream([tool, 'e', '-so', str(args.source), '-i!*.iso'])
    else:
        open_chunks = lambda: file_stream(args.source)
    try:
        written, read, incomplete = extract(open_chunks, args.output, args.resume)
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f'Extraction failed: {error}', file=sys.stderr)
        sys.exit(1)
    print(f'Read {read / 2**30:.2f} GiB of the image; extracted {written / 2**30:.2f} GiB to {args.output}')
    if incomplete:
        lost = sum(region.end - region.start for region in incomplete)
        print(f'{len(incomplete)} entries ({lost / 2**30:.2f} GiB) could not be read from the image:', file=sys.stderr)
        for region in sorted(incomplete, key=lambda region: region.start)[:40]:
            print(f'  {region.kind} {region.path.relative_to(args.output.parent)}', file=sys.stderr)
        sys.exit(2)


if __name__ == '__main__':
    main()
