#!/usr/bin/env python
from datetime import datetime
from datetime import timedelta
import os.path
import struct
import sys


def parse_box(f):
    buf = f.read(8)
    box_size = struct.unpack('>I', buf[:4])[0]
    box_type = str(buf[4:], 'utf-8')

    if box_size == 1:
        buf = f.read(8)
        box_size = struct.unpack('>Q', buf)[0]

    return box_size, box_type


def main(filename_in):
    containers = ('moov', 'trak', 'edts', 'mdia', 'minf', 'dinf', 'stbl')

    with open(filename_in, 'rb') as f_in:
        f_in.seek(0, 2)
        file_size = f_in.tell()

        cur = 0
        sc_table = []
        sz_table = []
        co_table = []
        while True:
            f_in.seek(cur)

            box_size, box_type = parse_box(f_in)
            if box_size == 0:
                box_size = file_size - cur

            if box_type in containers:
                box_size, box_type = parse_box(f_in)
                if box_size == 0:
                    box_size = file_size - cur
                cur += 8
            elif box_type == 'stsc':
                # Sample-to-Chunk Atoms
                buf = f_in.read(box_size - 8)

                version   = buf[0]
                flags     = buf[1:4]
                n_entries = struct.unpack('>I', buf[4:8])[0]

                for i in range(n_entries):
                    i0 = 8 + i*12
                    i1 = i0 + 12
                    if len(buf) < i1: break
                    first_chunk       = struct.unpack('>I', buf[i0:i0+4])[0]
                    samples_per_chunk = struct.unpack('>I', buf[i0+4:i0+8])[0]
                    sample_desc_id    = struct.unpack('>I', buf[i0+8:i0+12])[0]
                    sc_table.append((first_chunk, samples_per_chunk, sample_desc_id))
                    # print(f'{i:6d}: {(first_chunk, samples_per_chunk, sample_desc_id)}')
            elif box_type == 'stsz':
                #Sample Size Atoms
                buf = f_in.read(box_size - 8)

                version   = buf[0]
                flags     = buf[1:4]
                sample_size = struct.unpack('>I', buf[4:8])[0]
                n_entries = struct.unpack('>I', buf[8:12])[0]

                for i in range(n_entries):
                    i0 = 12 + i*4
                    i1 = i0 + 4
                    if len(buf) < i1: break
                    size = struct.unpack('>I', buf[i0:i1])[0]
                    sz_table.append(size)
                    # print(f'{i:6d}: {size}')
            elif box_type == 'stco':
                #Chunk Offset Atoms
                buf = f_in.read(box_size - 8)

                version   = buf[0]
                flags     = buf[1:4]
                n_entries = struct.unpack('>I', buf[4:8])[0]

                for i in range(n_entries):
                    i0 = 8 + i*4
                    i1 = i0 + 4
                    if len(buf) < i1: break
                    offset = struct.unpack('>I', buf[i0:i1])[0]
                    co_table.append(offset)
                    # print(f'{i:6d}: {offset}')
            elif box_type == 'co64':
                #64-bit chunk offset atoms
                buf = f_in.read(box_size - 8)

                version   = buf[0]
                flags     = buf[1:4]
                n_entries = struct.unpack('>I', buf[4:8])[0]

                for i in range(n_entries):
                    i0 = 8 + i*8
                    i1 = i0 + 8
                    if len(buf) < i1: break
                    offset = struct.unpack('>Q', buf[i0:i1])[0]
                    co_table.append(offset)
                    # print(f'{i:6d}: {offset}')

            if len(sc_table) != 0 and len(sz_table) != 0 and len(co_table) != 0:
                print('########################            ########################')
                i = 0
                l = 0
                while True:
                    m0, n, _ = sc_table[i]
                    if i + 1 < len(sc_table):
                        m1 = sc_table[i + 1][0]
                    else:
                        m1 = len(co_table) + 1

                    j = m0 - 1
                    while True:
                        offset = co_table[j]

                        k = 0
                        while True:
                            cur_temp = f_in.tell()
                            f_in.seek(offset)
                            buf = bytes([0x00, 0x00]) + f_in.read(6)
                            f_in.seek(cur_temp)
                            binary = struct.unpack('>Q', buf)[0]
                            mark = ' '
                            if sz_table[l] < 100: mark = 'v'
                            print(f'{mark}{offset:10d} {sz_table[l]:6d} {binary:059_b}')
                            offset += sz_table[l]
                            l += 1

                            k += 1
                            if k >= n:
                                break

                        j += 1
                        if j >= m1 - 1:
                            break

                    i += 1
                    if i >= len(sc_table):
                        break
                print('')

                sc_table = []
                sz_table = []
                co_table = []

            cur += box_size
            if cur >= file_size:
                break


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} in.mp4')
        sys.exit(1)

    filename_in = sys.argv[1]

    main(filename_in)
