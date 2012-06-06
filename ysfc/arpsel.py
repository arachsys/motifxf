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


def pack(version, items):
    count, entries, data = 0, "", ""
    for item in items:
        size = len(item['data']) - 8

        if version <= (1, 0, 1):
            entry = struct.pack(">4xI4x2I1x", size, len(data) + 12, count)
        else:
            entry = struct.pack(">4xI4x2I2x", size, len(data) + 12, count)

        entry += "%s\x00%s\x00" % (item['name'], item['filename'])
        if item.get('depends'):
            entry += '\x00'.join(item['depends']) + '\x00'

        entries += struct.pack(">4sI", "Entr", len(entry)) + entry
        data += item['data']
        count += 1

    count = struct.pack(">I", count)
    return count + entries, count + data


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


if len(sys.argv) < 2:
    sys.stderr.write("""\
Usage: %s IN1[:NUM,NUM,..] [IN2[:NUM,NUM,..]].. >OUT
Combines the arps from Yamaha YSFC files IN1, IN2, ... into a single X0G/X3G
file OUT, selecting just the specified arp numbers if the option :NUM,NUM,..
suffices are supplied. Arps are numbered from 001 as in the Motif user
interface.
""" % sys.argv[0])
    sys.exit(1)

out = []
for arg in sys.argv[1:]:
    if ':' in arg:
        arg, _, numbers = arg.rpartition(':')
        numbers = [int(number) - 1 for number in numbers.split(',')]
    else:
        numbers = xrange(0xffffffff)

    with open(arg, 'rb') as file:
        version, blocks = input(file = file, types = ['EARP', 'DARP'])
        arps = unpack(version, blocks['EARP'], blocks['DARP'])
        out += [arp for arp in arps if arp['number'] in numbers]

for number, arp in enumerate(out):
    arp['number'] = number
    arp['filename'] = "%03d-Arpeggio.arp" % number

if len(out) > 256:
    sys.stderr.write("Warning: Motif will refuse to read more than 256 arps\n")

if out:
    earp, darp = pack(version, out)
    output(version, { "EARP": earp, "DARP": darp })
