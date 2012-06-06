#!/bin/python

import struct
import sys

def input(file = sys.stdin, types = None):
    data = file.read(64)
    if len(data) != 64 or data[0:16].rstrip('\x00') != "YAMAHA-YSFC" \
                       or data[36:64] != 28 * '\xff':
        raise ValueError, "Invalid file format"

    try:
        version = tuple(map(int, data[16:32].rstrip('\x00').split('.')))
        size = struct.unpack(">I", data[32:36])[0]
        catalog = file.read(size)
        assert len(version) == 3 and len(catalog) == size
    except:
        raise ValueError, "Truncated file"

    blocks = {}
    while True:
        name = file.read(4)
        if not name:
            return version, blocks
        elif len(name) != 4:
            raise ValueError, "Truncated file"
        elif not name.isalpha() or not name.isupper():
            raise ValueError, "Invalid file format"
        try:
            size = struct.unpack(">I", file.read(4))[0]
            if not types or name in types:
                blocks[name] = file.read(size)
                assert len(blocks[name]) == size
            else:
                file.seek(size, 1)
        except:
            raise ValueError, "Truncated file"


def output(version, blocks, file = sys.stdout):
    file.write(struct.pack("16s", "YAMAHA-YSFC"))
    file.write(struct.pack("16s", '.'.join(map(str, version))))
    file.write(struct.pack(">I", 8*len(blocks)) + 28*'\xff')

    names = blocks.keys()
    names.sort(key = lambda n: '0' + n if n[0] == 'E' else '1' + n)

    offset = 64 + 8*len(names)
    for name in names:
        file.write(struct.pack(">4sI", name, offset))
        offset += 8 + len(blocks[name])

    for name in names:
        file.write(struct.pack(">4sI", name, len(blocks[name])))
        file.write(blocks[name])


version, blocks = input()
del blocks['ESYS'], blocks['DSYS']
output(version, blocks)
