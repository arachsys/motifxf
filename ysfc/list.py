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

    if version[0:2] != (1, 0) or version[2] not in [0, 1, 2]:
        raise ValueError, "Unsupported file format version"

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


def unpack(version, entries, data):
    count, cursor, items = struct.unpack_from(">I", entries)[0], 4, []
    while (cursor < len(entries)):
        magic, length = struct.unpack_from(">4sI", entries, cursor)
        if magic != "Entr" or cursor + length + 8 > len(entries):
            raise ValueError, "Invalid file format"

        size, offset, number = struct.unpack_from(">4xI4x2I", entries, cursor + 8)

        if version <= (1, 0, 1):
            names = entries[cursor + 29:cursor + length + 8]
        else:
            names = entries[cursor + 30:cursor + length + 8]
        names = names.rstrip('\x00').split('\x00')

        item = { 'number': number, 'name': names[0], 'filename': names[1] }
        if len(names) > 2:
            item['depends'] = names[2:]
        if data:
            item['data'] = data[offset - 8:offset + size]

        items.append(item)
        cursor += length + 8

    if len(items) != count:
        raise ValueError, "Invalid file format"
    else:
        return items


def bankname(number):
    bank, program = number >> 8, 1 + (number & 0xff)
    if bank in range(0x3f08, 0x3f10):
        return "USR%d:%03d" % (bank - 0x3f07, program)
    if bank == 0x3f28:
        return "USRDR:%03d" % program
    if bank in range(0x3f80, 0x3fc0):
        if program <= 128:
            return "SNG%d:SP%03d" % (bank - 0x3f7f, program)
        else:
            return "SNG%d:MV%03d" % (bank - 0x3f7f, program - 128)
    if bank in range(0x3fc0, 0x4000):
        if program <= 128:
            return "PTN%d:SP%03d" % (bank - 0x3fbf, program)
        else:
            return "PTN%d:MV%03d" % (bank - 0x3fbf, program - 128)
    return "0x%06x" % number


version, blocks = input()

for block in blocks.keys():
    if block[0] != 'E':
        continue
    for item in unpack(version, blocks[block], None):
        if block == 'EVCE':
            print "VCE %s %s" % (bankname(item['number']), item['name'])
        else:
            print "%3s %04d %s" % (block[1:], item['number'] + 1, item['name'])
