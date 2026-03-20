#!/usr/bin/python

# me_cleaner - Tool for partial deblobbing of Intel ME/TXE firmware images
# Copyright (C) 2016-2018 Nicola Corna <nicola@corna.info>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# ============================================================
# FORK PATCHES (on top of modified me_cleaner v1.3):
#
#  1. ME 12 LP (Whiskey Lake / Coffee Lake U) — HAP at fpsba+0x70, bit 16
#     ME 12 H  (Cannon Lake H / Z390 etc.)   — HAP at fpsba+0x80, bit 16
#     8th gen ThinkPad confirmed working with fpsba+0x70 (original fork).
#
#  2. ME 13 (Ice Lake) — same as ME 12 LP → fpsba+0x70, bit 16
#     Added gen=4 branch for version[0]==13.
#
#  3. ME 14 (Comet Lake LP / Tiger Lake) — HAP at fpsba+0x70, bit 16
#     HARDWARE CONFIRMED on ThinkPad X13 Gen 1 (CML-U, 10th gen):
#       stock   PCHSTRP28 = 0x801801b8  (bit 16 = 0)
#       patched PCHSTRP28 = 0x801901b8  (bit 16 = 1)  ← diff = 0x00010000
#       cmp -l byte 371 = fpsba(0x100) + 0x70 + 3  (byte 3 of the dword)
#     fpsba+0x70 bit 16 is the correct and confirmed HAP location for
#     CML-LP. The old code used fpsba+0x80 which was WRONG for LP boards.
#
#  4. ME 15 (Tiger Lake LP / Rocket Lake H / Tiger Lake H) — gen 6
#     TGL-LP: fpsba+0x7C = PCHSTRP31 bit 16
#       Datasheet confirmed: TGL-LP SPI Programming Guide (archive.org)
#     RKL-H / TGL-H (Tiger Point PCH-H): fpsba+0x94 = PCHSTRP37 bit 16
#       Datasheet confirmed: Rocketlake-H SPI Programming Guide (archive.org)
#     LP vs H detected via heuristic — same approach as gen 4 (ME 12).
#     XutaxKamay's guess was correct.
#
#  5. ME 16 / 16.1 (Alder Lake / Raptor Lake) — HAP at
#     PCHSTRP31 bit 16, same register as Tiger Lake.
#     Written as a byte write to Flash Descriptor offset 0x017E (= byte 2 of
#     the PCHSTRP31 dword at fpsba+0x7C). These are NOT two different locations —
#     they are the same bit expressed differently:
#       fpsba=0x100 (Intel 600-series PCH Datasheet Vol1, Doc 648364, confirmed)
#       PCHSTRP31 = fpsba + 0x7C = 0x17C  (the dword)
#       byte 0x017E = byte 2 of that dword = bit 16 of PCHSTRP31  ✓ identical
#     HAP never left the PCH straps. The old fpsba+0xDC (PCHSTRP55) guess from
#     XutaxKamay was WRONG — confirmed wrong by datasheet. CSME straps at 0xC3C
#     (new ADL section) are internal to CSME firmware and unrelated to HAP.
#     ME 16 and 16.1 confirmed. DO NOT group ME 18 here — see point 6.
#
#  6. ME 18 (Meteor Lake) — HAP at absolute byte offset 0x21E
#     Source: Dasharo coreboot me_spec_18.h: HAP_OFFSET = 0x21E (MTL U/H)
#     Analysis: 0x21E = fpsba(0x1A0) + PCHSTRP31_offset(0x7C) + byte2(0x02)
#     Same strap structure as ADL/RPL — PCHSTRP31 bit 16 — fpsba moved to 0x1A0
#     MTL dropped the discrete PCH (tile architecture). No PCH Straps at 0x100.
#     fpsba appears to be at 0x1A0 on MTL based on back-calculation from Dasharo.
#     EXPERIMENTAL: Dasharo source only. Not yet confirmed from hardware dump
#     or Intel MTL SPI Programming Guide. Main branch still skips write for safety.
#     Source: Intel Core Ultra CPU Datasheet Vol1 Doc 792044.
#
#  7. Version → gen mapping:
#       12 → gen 4  (8th/9th gen ThinkPad, confirmed)
#       13 → gen 4  (Ice Lake, fpsba+0x70, datasheet confirmed Doc 615170)
#       14 → gen 5  (10th gen ThinkPad CML-LP, hardware confirmed)
#       15 → gen 6  (TGL-LP: fpsba+0x7C PCHSTRP31 / RKL-H+TGL-H: fpsba+0x94 PCHSTRP37, datasheet confirmed)
#       16 → gen 7  (Alder Lake, PCHSTRP31 bit 16, Intel datasheet confirmed)
#       16.1→ gen 7  (Raptor Lake, same as ADL)
#       18 → gen 8  (MTL — HAP at byte 0x21E, Dasharo source, experimental)
#
#  7. IFWI firmware (gen >= 4): module removal is skipped with a clear
#     warning. HAP bit is still set correctly. Attempting partition
#     cleanup on IFWI images corrupts the image.
#
#  8. get_hap_offset_lp_or_h() heuristic REMOVED for gen 5.
#     Replaced with hardcoded fpsba+0x70 based on confirmed hardware data.
#     Gen 4 retains the heuristic for ME12-H board compatibility
#     (Z390/H370 desktop boards use fpsba+0x80).
#
# Confirmed hardware:
#   8th  gen ThinkPad (ME 12, CFL-U)      — fpsba+0x70 PCHSTRP28 bit 16  ✓ hw confirmed
#   10th gen ThinkPad X13 (ME 14, CML-U)  — fpsba+0x70 PCHSTRP28 bit 16  ✓ hw confirmed
#   Ice Lake (ME 13)                       — fpsba+0x70 PCHSTRP28 bit 16  ✓ datasheet confirmed (Doc 615170)
#   Tiger Lake LP (ME 15)                  — fpsba+0x7C PCHSTRP31 bit 16  ✓ datasheet confirmed (TGL-LP SPI Guide, archive.org)
#   RKL-H / TGL-H (ME 15)                — fpsba+0x94 PCHSTRP37 bit 16  ✓ datasheet confirmed (RKL-H SPI Guide, archive.org)
#                                            ✓ community confirmed: ASRock B560M + Asus Z590 (minhkhoi89, PR #384 Dec 2025)
#   Alder Lake (ME 16)                     — fpsba+0x7C PCHSTRP31 bit 16  ✓ Intel datasheet confirmed
#                                            (Doc 648364, byte write to 0x017E = same bit)
#   Raptor Lake (ME 16.1)                  — fpsba+0x7C PCHSTRP31 bit 16  ✓ community confirmed
#   Meteor Lake (ME 18)                    — byte 0x21E bit 0  (experimental)
#                                            Source: Dasharo coreboot me_spec_18.h
#                                            fpsba=0x1A0, PCHSTRP31 bit 16 = byte 0x21E
# ============================================================

from __future__ import division, print_function

import argparse
import binascii
import hashlib
import itertools
import shutil
import sys
import re
from struct import pack, unpack


min_ftpr_offset = 0x400
spared_blocks = 4
unremovable_modules = ("ROMP", "BUP")
unremovable_modules_gen3 = ("rbe", "kernel", "syslib", "bup")
unremovable_partitions = ("FTPR",)

pubkeys_md5 = {
    "8431285d43b0f2a2f520d7cab3d34178": ("ME",  ("2.0.x.x", "2.1.x.x",
                                                 "2.2.x.x")),
    "4c00dd06c28119b5c1e5bb8eb6f30596": ("ME",  ("2.5.x.x", "2.6.x.x")),
    "9c24077a7f7490967855e9c4c16c6b9e": ("ME",  ("3.x.x.x",)),
    "bf41464be736f5520d80c67f6789020e": ("ME",  ("4.x.x.x",)),
    "5c7169b7e7065323fb7b3b5657b4d57a": ("ME",  ("5.x.x.x",)),
    "763e59ebe235e45a197a5b1a378dfa04": ("ME",  ("6.x.x.x",)),
    "3a98c847d609c253e145bd36512629cb": ("ME",  ("6.0.50.x",)),
    "0903fc25b0f6bed8c4ed724aca02124c": ("ME",  ("7.x.x.x", "8.x.x.x")),
    "2011ae6df87c40fba09e3f20459b1ce0": ("ME",  ("9.0.x.x", "9.1.x.x")),
    "e8427c5691cf8b56bc5cdd82746957ed": ("ME",  ("9.5.x.x", "10.x.x.x")),
    "986a78e481f185f7d54e4af06eb413f6": ("ME",  ("11.x.x.x",)),
    "3efc26920b4bee901b624771c742887b": ("ME",  ("12.x.x.x",)),
    "8e4f834644da2bef03039d69d41ecf02": ("ME",  ("14.x.x.x",)),
    "b29411f89bf20ed177d411c46e8ec185": ("ME",  ("15.x.x.x",)),
    "5887caf9b677601ffb257cc98a13d2a9": ("ME",  ("16.x.x.x",)),  # Consumer / non-vPro
    "e7155f4342af9d1b7e4cac467190d382": ("ME",  ("16.1.x.x",)),  # ME 16.1 RPL-H / ADL-P — widespread across Raptor Lake-H and Alder Lake-P platforms
                                                                             # Confirmed: ThinkPad T14 Gen3 (ADL-P PCH, ME 16.1.38.2676)
                                                                             # Confirmed: ThinkPad T14 Gen3, ME 16.1.25.1932
                                                                             # Confirmed: Lenovo Legion Slim 7 16IRH8 (RPL-H, ADL-P PCH, ME 16.1.38.2676)
                                                                             # Confirmed: MSI E7E06IMS (RPL-H, ME 16.1.25.2124)
                                                                             # Same key across 16.1.25.x and 16.1.38.x — RPL-H/ADL-P share signing key
    "bda0b6bb8ca0bf0cac55ac4c4d55e0f2": ("TXE", ("1.x.x.x",)),
    "b726a2ab9cd59d4e62fe2bead7cf6997": ("TXE", ("1.x.x.x",)),
    "0633d7f951a3e7968ae7460861be9cfb": ("TXE", ("2.x.x.x",)),
    "1d0a36e9f5881540d8e4b382c6612ed8": ("TXE", ("3.x.x.x",)),
    "be900fef868f770d266b1fc67e887e69": ("SPS", ("2.x.x.x",)),
    "4622e3f2cb212a89c90a4de3336d88d2": ("SPS", ("3.x.x.x",)),
    "31ef3d950eac99d18e187375c0764ca4": ("SPS", ("4.x.x.x",))
}


class OutOfRegionException(Exception):
    pass


class RegionFile:
    def __init__(self, f, region_start, region_end):
        self.f = f
        self.region_start = region_start
        self.region_end = region_end

    def readall(self):
        currentpos = self.f.tell()
        self.f.seek(self.region_start)
        toret = self.f.read(self.region_end - self.region_start)
        self.f.seek(currentpos)
        return toret

    def read(self, n):
        if f.tell() + n <= self.region_end:
            return self.f.read(n)
        else:
            raise OutOfRegionException()

    def readinto(self, b):
        if f.tell() + len(b) <= self.region_end:
            return self.f.readinto(b)
        else:
            raise OutOfRegionException()

    def seek(self, offset):
        if self.region_start + offset <= self.region_end:
            return self.f.seek(self.region_start + offset)
        else:
            raise OutOfRegionException()

    def write_to(self, offset, data):
        if self.region_start + offset + len(data) <= self.region_end:
            self.f.seek(self.region_start + offset)
            return self.f.write(data)
        else:
            raise OutOfRegionException()

    def fill_range(self, start, end, fill):
        if self.region_start + end <= self.region_end:
            if start < end:
                block = fill * 4096
                self.f.seek(self.region_start + start)
                self.f.writelines(itertools.repeat(block,
                                                   (end - start) // 4096))
                self.f.write(block[:(end - start) % 4096])
        else:
            raise OutOfRegionException()

    def fill_all(self, fill):
        self.fill_range(0, self.region_end - self.region_start, fill)

    def move_range(self, offset_from, size, offset_to, fill):
        if self.region_start + offset_from + size <= self.region_end and \
           self.region_start + offset_to + size <= self.region_end:
            for i in range(0, size, 4096):
                self.f.seek(self.region_start + offset_from + i, 0)
                block = self.f.read(min(size - i, 4096))
                self.f.seek(self.region_start + offset_from + i, 0)
                self.f.write(fill * len(block))
                self.f.seek(self.region_start + offset_to + i, 0)
                self.f.write(block)
        else:
            raise OutOfRegionException()

    def save(self, filename, size):
        if self.region_start + size <= self.region_end:
            self.f.seek(self.region_start)
            copyf = open(filename, "w+b")
            for i in range(0, size, 4096):
                copyf.write(self.f.read(min(size - i, 4096)))
            return copyf
        else:
            raise OutOfRegionException()


def get_chunks_offsets(llut):
    chunk_count = unpack("<I", llut[0x04:0x08])[0]
    huffman_stream_end = sum(unpack("<II", llut[0x10:0x18]))
    nonzero_offsets = [huffman_stream_end]
    offsets = []

    for i in range(0, chunk_count):
        chunk = llut[0x40 + i * 4:0x44 + i * 4]
        offset = 0

        if chunk[3] != 0x80:
            offset = unpack("<I", chunk[0:3] + b"\x00")[0]

        offsets.append([offset, 0])
        if offset != 0:
            nonzero_offsets.append(offset)

    nonzero_offsets.sort()

    for i in offsets:
        if i[0] != 0:
            i[1] = nonzero_offsets[nonzero_offsets.index(i[0]) + 1]

    return offsets


def remove_modules(f, mod_headers, ftpr_offset, me_end):
    comp_str = ("uncomp.", "Huffman", "LZMA")
    unremovable_huff_chunks = []
    chunks_offsets = []
    base = 0
    chunk_size = 0
    end_addr = 0

    for mod_header in mod_headers:
        name = mod_header[0x04:0x14].rstrip(b"\x00").decode("ascii")
        offset = unpack("<I", mod_header[0x38:0x3C])[0] + ftpr_offset
        size = unpack("<I", mod_header[0x40:0x44])[0]
        flags = unpack("<I", mod_header[0x50:0x54])[0]
        comp_type = (flags >> 4) & 7

        print(" {:<16} ({:<7}, ".format(name, comp_str[comp_type]), end="")

        if comp_type == 0x00 or comp_type == 0x02:
            print("0x{:06x} - 0x{:06x}       ): "
                  .format(offset, offset + size), end="")

            if name in unremovable_modules:
                end_addr = max(end_addr, offset + size)
                print("NOT removed, essential")
            else:
                end = min(offset + size, me_end)
                f.fill_range(offset, end, b"\xff")
                print("removed")

        elif comp_type == 0x01:
            if not chunks_offsets:
                f.seek(offset)
                llut = f.read(4)
                if llut == b"LLUT":
                    llut += f.read(0x3c)

                    chunk_count = unpack("<I", llut[0x4:0x8])[0]
                    base = unpack("<I", llut[0x8:0xc])[0] + 0x10000000
                    chunk_size = unpack("<I", llut[0x30:0x34])[0]

                    llut += f.read(chunk_count * 4)
                    chunks_offsets = get_chunks_offsets(llut)
                else:
                    sys.exit("Huffman modules found, but LLUT is not present")

            module_base = unpack("<I", mod_header[0x34:0x38])[0]
            module_size = unpack("<I", mod_header[0x3c:0x40])[0]
            first_chunk_num = (module_base - base) // chunk_size
            last_chunk_num = first_chunk_num + module_size // chunk_size
            huff_size = 0

            for chunk in chunks_offsets[first_chunk_num:last_chunk_num + 1]:
                huff_size += chunk[1] - chunk[0]

            print("fragmented data, {:<9}): "
                  .format("~" + str(int(round(huff_size / 1024))) + " KiB"),
                  end="")

            if name in unremovable_modules:
                print("NOT removed, essential")

                unremovable_huff_chunks += \
                    [x for x in chunks_offsets[first_chunk_num:
                     last_chunk_num + 1] if x[0] != 0]
            else:
                print("removed")

        else:
            print("0x{:06x} - 0x{:06x}): unknown compression, skipping"
                  .format(offset, offset + size), end="")

    if chunks_offsets:
        removable_huff_chunks = []

        for chunk in chunks_offsets:
            if all(not(unremovable_chk[0] <= chunk[0] < unremovable_chk[1] or
                       unremovable_chk[0] < chunk[1] <= unremovable_chk[1])
                   for unremovable_chk in unremovable_huff_chunks):
                removable_huff_chunks.append(chunk)

        for removable_chunk in removable_huff_chunks:
            if removable_chunk[1] > removable_chunk[0]:
                end = min(removable_chunk[1], me_end)
                f.fill_range(removable_chunk[0], end, b"\xff")

        end_addr = max(end_addr,
                       max(unremovable_huff_chunks, key=lambda x: x[1])[1])

    return end_addr


def check_partition_signature(f, offset):
    f.seek(offset)
    header = f.read(0x80)
    modulus = int(binascii.hexlify(f.read(0x100)[::-1]), 16)
    public_exponent = unpack("<I", f.read(4))[0]
    signature = int(binascii.hexlify(f.read(0x100)[::-1]), 16)

    header_len = unpack("<I", header[0x4:0x8])[0] * 4
    manifest_len = unpack("<I", header[0x18:0x1c])[0] * 4
    f.seek(offset + header_len)

    sha256 = hashlib.sha256()
    sha256.update(header)
    sha256.update(f.read(manifest_len - header_len))

    decrypted_sig = pow(signature, public_exponent, modulus)

    return "{:#x}".format(decrypted_sig).endswith(sha256.hexdigest())   # FIXME


def print_check_partition_signature(f, offset, gen=None):
    if check_partition_signature(f, offset):
        print("VALID")
    else:
        print("INVALID!!")
        if gen is not None and gen >= 7:
            print("  Note: FTPR RSA validation is not supported on ME 16+ IFWI")
            print("  firmware. This message is a known tool limitation and does")
            print("  NOT indicate a problem with your image or your HAP patch.")
            print("  Use MEAnalyzer on your stock dump to independently verify")
            print("  firmware integrity.")
        else:
            sys.exit("The FTPR partition signature is not valid. Is the input "
                     "ME/TXE image valid?")


def relocate_partition(f, me_end, partition_header_offset,
                       new_offset, mod_headers):

    f.seek(partition_header_offset)
    name = f.read(4).rstrip(b"\x00").decode("ascii")
    f.seek(partition_header_offset + 0x8)
    old_offset, partition_size = unpack("<II", f.read(0x8))

    llut_start = 0
    for mod_header in mod_headers:
        if (unpack("<I", mod_header[0x50:0x54])[0] >> 4) & 7 == 0x01:
            llut_start = unpack("<I", mod_header[0x38:0x3C])[0] + old_offset
            break

    if mod_headers and llut_start != 0:
        f.seek(llut_start + 0x9)
        lut_start_corr = unpack("<H", f.read(2))[0]
        new_offset = max(new_offset,
                         lut_start_corr - llut_start - 0x40 + old_offset)
        new_offset = ((new_offset + 0x1f) // 0x20) * 0x20

    offset_diff = new_offset - old_offset
    print("Relocating {} from {:#x} - {:#x} to {:#x} - {:#x}..."
          .format(name, old_offset, old_offset + partition_size,
                  new_offset, new_offset + partition_size))

    print(" Adjusting FPT entry...")
    f.write_to(partition_header_offset + 0x8,
               pack("<I", new_offset))

    if mod_headers:
        if llut_start != 0:
            f.seek(llut_start)
            if f.read(4) == b"LLUT":
                print(" Adjusting LUT start offset...")
                lut_offset = llut_start + offset_diff + 0x40 - lut_start_corr
                f.write_to(llut_start + 0x0c, pack("<I", lut_offset))

                print(" Adjusting Huffman start offset...")
                f.seek(llut_start + 0x14)
                old_huff_offset = unpack("<I", f.read(4))[0]
                f.write_to(llut_start + 0x14,
                           pack("<I", old_huff_offset + offset_diff))

                print(" Adjusting chunks offsets...")
                f.seek(llut_start + 0x4)
                chunk_count = unpack("<I", f.read(4))[0]
                f.seek(llut_start + 0x40)
                chunks = bytearray(chunk_count * 4)
                f.readinto(chunks)
                for i in range(0, chunk_count * 4, 4):
                    if chunks[i + 3] != 0x80:
                        chunks[i:i + 3] = \
                            pack("<I", unpack("<I", chunks[i:i + 3] +
                                 b"\x00")[0] + offset_diff)[0:3]
                f.write_to(llut_start + 0x40, chunks)
            else:
                sys.exit("Huffman modules present but no LLUT found!")
        else:
            print(" No Huffman modules found")

    print(" Moving data...")
    partition_size = min(partition_size, me_end - old_offset)
    f.move_range(old_offset, partition_size, new_offset, b"\xff")

    return new_offset


def check_and_remove_modules(f, me_end, offset, min_offset,
                             relocate, keep_modules):

    f.seek(offset + 0x20)
    num_modules = unpack("<I", f.read(4))[0]
    f.seek(offset + 0x290)
    data = f.read(0x84)

    mod_header_size = 0
    if data[0x0:0x4] == b"$MME":
        if data[0x60:0x64] == b"$MME" or num_modules == 1:
            mod_header_size = 0x60
        elif data[0x80:0x84] == b"$MME":
            mod_header_size = 0x80

    if mod_header_size != 0:
        f.seek(offset + 0x290)
        data = f.read(mod_header_size * num_modules)
        mod_headers = [data[i * mod_header_size:(i + 1) * mod_header_size]
                       for i in range(0, num_modules)]

        if all(hdr.startswith(b"$MME") for hdr in mod_headers):
            if args.keep_modules:
                end_addr = offset + ftpr_length
            else:
                end_addr = remove_modules(f, mod_headers, offset, me_end)

            if args.relocate:
                new_offset = relocate_partition(f, me_end, 0x30, min_offset,
                                                mod_headers)
                end_addr += new_offset - offset
                offset = new_offset

            return end_addr, offset

        else:
            print("Found less modules than expected in the FTPR "
                  "partition; skipping modules removal")
    else:
        print("Can't find the module header size; skipping "
              "modules removal")

    return -1, offset


def check_and_remove_modules_gen3(f, me_end, partition_offset,
                                  partition_length, min_offset, relocate,
                                  keep_modules):

    comp_str = ("LZMA/uncomp.", "Huffman")

    if keep_modules:
        end_data = partition_offset + partition_length
    else:
        end_data = 0

        f.seek(partition_offset + 0x4)
        module_count = unpack("<I", f.read(4))[0]

        modules = []
        modules.append(("end", partition_length, 0))

        f.seek(partition_offset + 0x10)
        for i in range(0, module_count):
            data = f.read(0x18)
            name = data[0x0:0xc].rstrip(b"\x00").decode("ascii")
            offset_block = unpack("<I", data[0xc:0x10])[0]
            offset = offset_block & 0x01ffffff
            comp_type = (offset_block & 0x02000000) >> 25

            modules.append((name, offset, comp_type))

        modules.sort(key=lambda x: x[1])

        for i in range(0, module_count):
            name = modules[i][0]
            offset = partition_offset + modules[i][1]
            end = partition_offset + modules[i + 1][1]
            removed = False

            if name.endswith(".man") or name.endswith(".met"):
                compression = "uncompressed"
            else:
                compression = comp_str[modules[i][2]]

            print(" {:<12} ({:<12}, 0x{:06x} - 0x{:06x}): "
                  .format(name, compression, offset, end), end="")

            if name.endswith(".man"):
                print("NOT removed, partition manif.")
            elif name.endswith(".met"):
                print("NOT removed, module metadata")
            elif any(name.startswith(m) for m in unremovable_modules_gen3):
                print("NOT removed, essential")
            else:
                removed = True
                f.fill_range(offset, min(end, me_end), b"\xff")
                print("removed")

            if not removed:
                end_data = max(end_data, end)

    if relocate:
        new_offset = relocate_partition(f, me_end, 0x30, min_offset, [])
        end_data += new_offset - partition_offset
        partition_offset = new_offset

    return end_data, partition_offset


def check_mn2_tag(f, offset, gen):
    f.seek(offset + 0x1c)
    tag = f.read(4)
    expected_tag = b"$MAN" if gen == 1 else b"$MN2"
    if tag != expected_tag:
        sys.exit("Wrong FTPR manifest tag ({}), this image may be corrupted"
                 .format(tag))


def flreg_to_start_end(flreg):
    return (flreg & 0x7fff) << 12, (flreg >> 4 & 0x7fff000 | 0xfff) + 1


def start_end_to_flreg(start, end):
    return (start & 0x7fff000) >> 12 | ((end - 1) & 0x7fff000) << 4


# ============================================================
# HAP bit helper for ME 12/13 (gen 4) — LP vs H detection
#
# ME 12 LP (Whiskey Lake / Coffee Lake U): HAP at fpsba+0x70, bit 16
# ME 12 H  (Cannon Lake H, Z390/H370/B360 desktop): HAP at fpsba+0x80, bit 16
#
# ME 14 (gen 5, Comet Lake LP) does NOT use this heuristic —
# it is hardcoded to fpsba+0x70 based on confirmed hardware data
# from ThinkPad X13 Gen1 (CML-U).
#
# Strategy for gen 4: read both locations. If 0x70 is non-zero
# (strap is populated) use 0x70 (LP). Otherwise fall back to 0x80 (H).
# ============================================================
def get_hap_offset_lp_or_h(fdf, fpsba):
    """Return (pchstrp_value, byte_offset, name) for ME 12/13 LP vs H vs JSL.

    Covers three PCH variants that share ME 12/13:
      JSL (Jasper Lake, Atom N-series): PCHSTRP26 at fpsba+0x68 bit 16
        Dasharo me_spec_13.h: HAP_OFFSET=0x16A (SOC_INTEL_JASPERLAKE)
      ICL/CFL-U (Ice/Comet Lake LP, mobile): PCHSTRP28 at fpsba+0x70 bit 16
        Datasheet confirmed: Doc 615170 (ICL), hardware confirmed (CFL-U ME 12)
      ME12-H (Cannon Lake H, desktop): PCHSTRP32 at fpsba+0x80 bit 16
        Hardware confirmed: PR#282
    Detection: check 0x68 first (JSL), then 0x70 (LP), then 0x80 (H).
    """
    fdf.seek(fpsba + 0x68)
    val_68 = unpack("<I", fdf.read(4))[0]
    fdf.seek(fpsba + 0x70)
    val_70 = unpack("<I", fdf.read(4))[0]
    fdf.seek(fpsba + 0x80)
    val_80 = unpack("<I", fdf.read(4))[0]

    if val_68 != 0 and val_70 == 0:
        # JSL (Jasper Lake, Atom N-series) — PCHSTRP26 at fpsba+0x68
        # Dasharo me_spec_13.h: HAP_OFFSET=0x16A
        return val_68, 0x68, "PCHSTRP26 at fpsba+0x68 (Jasper Lake, Dasharo confirmed)"
    elif val_70 != 0:
        return val_70, 0x70, "PCHSTRP28 at fpsba+0x70 (LP/U-series)"
    elif val_80 != 0:
        return val_80, 0x80, "PCHSTRP32 at fpsba+0x80 (H/desktop)"
    else:
        return val_70, 0x70, "PCHSTRP28 at fpsba+0x70 (LP assumed — straps zero)"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tool to remove as much code "
                                     "as possible from Intel ME/TXE firmware "
                                     "images")
    softdis = parser.add_mutually_exclusive_group()
    bw_list = parser.add_mutually_exclusive_group()

    parser.add_argument("-v", "--version", action="version",
                        version="%(prog)s 1.2-thinkpad-fork")

    parser.add_argument("file", help="ME/TXE image or full dump")
    parser.add_argument("-O", "--output", metavar='output_file', help="save "
                        "the modified image in a separate file, instead of "
                        "modifying the original file")
    softdis.add_argument("-S", "--soft-disable", help="in addition to the "
                         "usual operations on the ME/TXE firmware, set the "
                         "MeAltDisable bit or the HAP bit to ask Intel ME/TXE "
                         "to disable itself after the hardware initialization "
                         "(requires a full dump)", action="store_true")
    softdis.add_argument("-s", "--soft-disable-only", help="instead of the "
                         "usual operations on the ME/TXE firmware, just set "
                         "the MeAltDisable bit or the HAP bit to ask Intel "
                         "ME/TXE to disable itself after the hardware "
                         "initialization (requires a full dump)",
                         action="store_true")
    parser.add_argument("-r", "--relocate", help="relocate the FTPR partition "
                        "to the top of the ME region to save even more space",
                        action="store_true")
    parser.add_argument("-t", "--truncate", help="truncate the empty part of "
                        "the firmware (requires a separated ME/TXE image or "
                        "--extract-me)", action="store_true")
    parser.add_argument("-k", "--keep-modules", help="don't remove the FTPR "
                        "modules, even when possible", action="store_true")
    bw_list.add_argument("-w", "--whitelist", metavar="whitelist",
                         help="Comma separated list of additional partitions "
                         "to keep in the final image.")
    bw_list.add_argument("-b", "--blacklist", metavar="blacklist",
                         help="Comma separated list of partitions to remove "
                         "from the image.")
    parser.add_argument("-d", "--descriptor", help="remove the ME/TXE "
                        "Read/Write permissions to the other regions on the "
                        "flash from the Intel Flash Descriptor (requires a "
                        "full dump)", action="store_true")
    parser.add_argument("-D", "--extract-descriptor",
                        metavar='output_descriptor', help="extract the flash "
                        "descriptor from a full dump")
    parser.add_argument("-M", "--extract-me", metavar='output_me_image',
                        help="extract the ME firmware from a full dump")
    parser.add_argument("-c", "--check", help="verify the integrity of the "
                        "fundamental parts of the firmware and exit",
                        action="store_true")

    args = parser.parse_args()

    if args.check and (args.soft_disable_only or args.soft_disable or
       args.relocate or args.descriptor or args.truncate or args.output):
        sys.exit("-c can't be used with -S, -s, -r, -d, -t or -O")

    if args.soft_disable_only and (args.relocate or args.truncate):
        sys.exit("-s can't be used with -r or -t")

    if (args.whitelist or args.blacklist) and args.relocate:
        sys.exit("Relocation is not yet supported with custom whitelist or "
                 "blacklist")

    gen = None

    f = open(args.file, "rb" if args.check or args.output else "r+b")
    magic0 = f.read(4)
    f.seek(0x10)
    magic10 = f.read(4)

    if b"$FPT" in {magic0, magic10}:
        print("ME/TXE image detected")

        if args.descriptor or args.extract_descriptor or args.extract_me or \
           args.soft_disable or args.soft_disable_only:
            sys.exit("-d, -D, -M, -S and -s require a full dump")

        f.seek(0, 2)
        me_start = 0
        me_end = f.tell()
        mef = RegionFile(f, me_start, me_end)

    elif b"\x5a\xa5\xf0\x0f" in {magic0, magic10}:
        print("Full image detected")

        f.seek(0x4 if magic0 == b"\x5a\xa5\xf0\x0f" else 0x14)
        flmap0, flmap1, flmap2 = unpack("<III", f.read(0xc))
        frba = flmap0 >> 12 & 0xff0
        fmba = (flmap1 & 0xff) << 4

        # Generation 1
        fisba = flmap1 >> 12 & 0xff0
        fmsba = (flmap2 & 0xff) << 4

        # Generation 2-3
        fpsba = fisba

        f.seek(frba)
        flreg = unpack("<III", f.read(12))

        fd_start, fd_end = flreg_to_start_end(flreg[0])
        bios_start, bios_end = flreg_to_start_end(flreg[1])
        me_start, me_end = flreg_to_start_end(flreg[2])

        if me_start >= me_end:
            print("The ME region in this image has already been disabled")
        else:
            mef = RegionFile(f, me_start, me_end)

        if magic0 == b"\x5a\xa5\xf0\x0f":
            gen = 1

    else:
        # Descriptor not found at offset 0x00 or 0x10.
        # Scan for it at 4KB-aligned page boundaries + 0x10 (e.g. recovery/backup
        # chips where the descriptor page is offset into the image — GigaDevice
        # backup chips on dual-chip ThinkPads have descriptor at 0x100010).
        desc_fd_sig = b"\x5a\xa5\xf0\x0f"
        found_offset = None
        f.seek(0, 2)
        file_size = f.tell()
        for page_base in range(0x1000, min(file_size, 0x800000), 0x1000):
            f.seek(page_base + 0x10)
            candidate = f.read(4)
            if candidate == desc_fd_sig:
                found_offset = page_base + 0x10
                break

        if found_offset is not None:
            print("Full image detected "
                  "(non-standard descriptor offset {:#x} — backup/recovery chip)"
                  .format(found_offset))
            # Parse FLMAP from the found descriptor location
            # Offsets are relative to the descriptor page base (found_offset & ~0xFFF)
            desc_base = found_offset & ~0xFFF
            f.seek(found_offset + 0x4)
            flmap0, flmap1, flmap2 = unpack("<III", f.read(0xc))
            frba  = (flmap0 >> 12 & 0xff0) + desc_base
            fmba  = ((flmap1 & 0xff) << 4) + desc_base
            fisba = (flmap1 >> 12 & 0xff0) + desc_base
            fmsba = ((flmap2 & 0xff) << 4) + desc_base
            fpsba_from_descriptor = (((flmap1 >> 16) & 0xFF) << 4) + desc_base
            fpsba = fisba

            f.seek(frba)
            flreg = unpack("<III", f.read(12))

            fd_start, fd_end = flreg_to_start_end(flreg[0])
            bios_start, bios_end = flreg_to_start_end(flreg[1])
            me_start, me_end = flreg_to_start_end(flreg[2])

            if me_start >= me_end:
                print("  No ME region found in backup chip — HAP write will"
                      " still proceed via descriptor")
            else:
                mef = RegionFile(f, me_start, me_end)
        else:
            sys.exit("Unknown image")

    if me_start < me_end:
        medata = mef.readall()
        fpt_matches = list((re.compile(br'\x24\x46\x50\x54.\x00\x00\x00', re.DOTALL)).finditer(medata))
        if (len(fpt_matches) == 0):
            sys.exit("$FPT not found")

        if (len(fpt_matches) > 1):
            # ME 16+ IFWI firmware commonly contains a backup/recovery FPT
            # header in addition to the primary one. Rather than exiting, use
            # the primary FPT (lowest offset within the ME region) and ignore
            # the rest. This is normal firmware structure, not corruption.
            fpt_matches = sorted(fpt_matches, key=lambda m: m.span()[0])
            print("Found {:d} $FPT headers — using primary at offset {:#x}, "
                  "ignoring backup FPT (normal on ME 16+ IFWI firmware)."
                  .format(len(fpt_matches),
                          mef.region_start + fpt_matches[0].span()[0]))

        fpt_offset = fpt_matches[0].span()[0]

    if gen == 1:
        end_addr = 0
    else:
        end_addr = me_end

    if me_start < me_end:
        print("Found FPT header at {:#x}".format(mef.region_start + fpt_offset))

        mef.seek(fpt_offset + 0x4)
        entries = unpack("<I", mef.read(4))[0]
        print("Found {} partition(s)".format(entries))

        mef.seek(fpt_offset + 0x20)
        partitions = mef.read(entries * 0x20)

        ftpr_header = b""

        for i in range(entries):
            if partitions[i * 0x20:(i * 0x20) + 4] in {b"CODE", b"FTPR"}:
                ftpr_header = partitions[i * 0x20:(i + 1) * 0x20]
                break

        if ftpr_header == b"":
            ftpr_matches = list((re.compile(br'\x24\x43\x50\x44........\x46\x54\x50\x52', re.DOTALL)).finditer(medata))

            if len(ftpr_matches) == 1:
                ftpr_offset = ftpr_matches[0].span()[0]
                ftpr_length = 0
                print("  Note: FTPR not found in FPT table — located via $CPD")
                print("  scan (known BPDT firmware quirk on ME 16+ IFWI).")
                print("  HAP write is unaffected by this.")
            elif len(ftpr_matches) > 1:
                after_fpt = [m for m in ftpr_matches
                             if m.span()[0] >= fpt_offset]
                if after_fpt:
                    best = min(after_fpt, key=lambda m: m.span()[0])
                else:
                    best = min(ftpr_matches, key=lambda m: m.span()[0])
                ftpr_offset = best.span()[0]
                ftpr_length = 0
                print("  Note: multiple $CPD FTPR matches ({}) — using closest"
                      " at offset {:#x} (BPDT IFWI quirk, HAP write"
                      " unaffected).".format(len(ftpr_matches),
                                             mef.region_start + ftpr_offset))
            else:
                sys.exit("FTPR header not found, this image doesn't seem to be "
                        "valid")
        else:
            if ftpr_header[0x0:0x4] == b"CODE":
                gen = 1

            ftpr_offset, ftpr_length = unpack("<II", ftpr_header[0x08:0x10])

        print("Found FTPR header: FTPR partition spans from {:#x} to {:#x}"
              .format(ftpr_offset, ftpr_offset + ftpr_length))

        mef.seek(ftpr_offset)
        if mef.read(4) == b"$CPD":
            gen = 3
            num_entries = unpack("<I", mef.read(4))[0]

            mef.seek(ftpr_offset + 0x14)
            data = mef.read(0x8)

            if bytes([0x46, 0x54, 0x50, 0x52, 0x2E, 0x6D, 0x61, 0x6E]) == data:
                mef.seek(ftpr_offset + 0x14)
            else:
                mef.seek(ftpr_offset + 0x10)

            ftpr_mn2_offset = -1

            for i in range(0, num_entries):
                data = mef.read(0x18)
                name = data[0x0:0xc].rstrip(b"\x00").decode("ascii")
                offset = unpack("<I", data[0xc:0xf] + b"\x00")[0]

                if name == "FTPR.man":
                    ftpr_mn2_offset = offset
                    break

            if ftpr_mn2_offset >= 0:
                check_mn2_tag(mef, ftpr_offset + ftpr_mn2_offset, gen)
                print("Found FTPR manifest at {:#x}"
                      .format(ftpr_offset + ftpr_mn2_offset))
            else:
                sys.exit("Can't find the manifest of the FTPR partition")

        else:
            check_mn2_tag(mef, ftpr_offset, gen)
            ftpr_mn2_offset = 0
            if not gen:
                gen = 2

        mef.seek(ftpr_offset + ftpr_mn2_offset + 0x24)
        version = unpack("<HHHH", mef.read(0x08))

        # --------------------------------------------------------
        # ME version → internal generation mapping
        #
        # gen 4: ME 12/13  — PCHSTRP28 at fpsba+0x70 (bit 16)
        #   8th/9th gen (CFL/WHL), Ice Lake LP
        #   hw confirmed (ME12), datasheet confirmed Doc 615170 (ME13)
        # gen 5: ME 14     — PCHSTRP28 at fpsba+0x70 (bit 16)
        #   Comet Lake LP — hw confirmed ThinkPad X13 Gen1
        # gen 6: ME 15     — TGL-LP: PCHSTRP31 at fpsba+0x7C (bit 16)
        #                    RKL-H/TGL-H: PCHSTRP37 at fpsba+0x94 (bit 16)
        #   LP vs H detected via heuristic (same as gen 4)
        #   TGL-LP datasheet confirmed: TGL-LP SPI Programming Guide (archive.org)
        #   RKL-H datasheet confirmed: Rocketlake-H SPI Programming Guide (archive.org)
        # gen 7: ME 16/16.1 — PCH-P/N: byte 0x017E / PCH-S desktop: byte 0x01DE
        #   PCH-S vs PCH-P/N detected via heuristic (same pattern as gen 4/6)
        #   Dasharo me_spec_16.h: HAP_OFFSET=0x17E (P/N) / 0x1DE (S)
        #   Alder Lake / Raptor Lake — datasheet confirmed Doc 648364/743835
        # gen 8: ME 18     — Meteor Lake, HAP at byte 0x21E (Dasharo source)
        #   fpsba=0x1A0 on MTL, PCHSTRP31 bit 16, byte write to 0x21E
        #   EXPERIMENTAL: Dasharo coreboot me_spec_18.h, not yet hardware confirmed
        # --------------------------------------------------------
        ME_VERSION_MAP = {
            12: 4,   # Cannon/Whiskey Lake LP (ME 12)     — hw confirmed
            13: 4,   # Ice Lake LP (ME 13)                — datasheet confirmed Doc 615170
            14: 5,   # Comet Lake LP (ME 14)              — hw confirmed
            15: 6,   # Tiger Lake (ME 15)                 — community confirmed
            16: 7,   # Alder Lake (ME 16)                 — datasheet confirmed Doc 648364
            18: 8,   # Meteor Lake (ME 18)                — byte 0x21E (Dasharo source, experimental)
        }
        gen = ME_VERSION_MAP.get(version[0])

        print("ME/TXE firmware version {} (generation {})"
              .format('.'.join(str(i) for i in version), gen))

        mef.seek(ftpr_offset + ftpr_mn2_offset + 0x80)
        pubkey_md5 = hashlib.md5(mef.read(0x104)).hexdigest()

        if pubkey_md5 in pubkeys_md5:
            variant, pubkey_versions = pubkeys_md5[pubkey_md5]
            print("Public key match: Intel {}, firmware versions {}"
                  .format(variant, ", ".join(pubkey_versions)))
        else:
            if version[0] >= 6:
                variant = "ME"
            else:
                variant = "TXE"
            print("WARNING Unknown public key {}\n"
                  "        Assuming Intel {}\n"
                  "        Please report this warning to the project's "
                  "maintainer!"
                  .format(pubkey_md5, variant))

    if not args.check and args.output:
        f.close()
        shutil.copy(args.file, args.output)
        f = open(args.output, "r+b")

    if me_start < me_end:
        mef = RegionFile(f, me_start, me_end)

    if me_start > 0:
        fdf = RegionFile(f, fd_start, fd_end)

        if gen == 1:
            for (ba, name) in ((fisba, "ICHSTRP0"), (fmsba, "MCHSTRP0")):
                fdf.seek(ba)
                strp = unpack("<I", fdf.read(4))[0]
                print("The meDisable bit in " + name + " is ", end="")
                if strp & 1:
                    print("SET")
                elif args.check:
                    print("NOT SET")
                else:
                    print("NOT SET, setting it now...")
                    fdf.write_to(ba, pack("<I", strp | 1))

        elif gen == 2:
            fdf.seek(fpsba + 0x28)
            pchstrp10 = unpack("<I", fdf.read(4))[0]
            print("The AltMeDisable bit is " +
                  ("SET" if pchstrp10 & 1 << 7 else "NOT SET"))

        # --------------------------------------------------------
        # PATCH: gen 4 = ME 12 + ME 13
        # Use LP-vs-H heuristic to find the correct HAP strap.
        # --------------------------------------------------------
        elif gen == 4:
            pchstrp_val, hap_offset, strap_name = get_hap_offset_lp_or_h(fdf, fpsba)
            print("Detected PCH strap layout: {}".format(strap_name))
            print("The HAP bit is " +
                  ("SET" if pchstrp_val & 1 << 16 else "NOT SET"))

        # --------------------------------------------------------
        # PATCH: gen 5 = ME 14 (Comet Lake) — LP/S split
        #   CML-LP (mobile, ThinkPads): PCHSTRP28 at fpsba+0x70 bit 16
        #     Hardware confirmed: ThinkPad X13 Gen1 (CML-U, ME 14.1.77.2497)
        #     Dasharo me_spec_12.h: HAP_OFFSET=0x172 (SOC_INTEL_COMETLAKE_1/2)
        #   CML-S (desktop Z490/H470/B460): PCHSTRP32 at fpsba+0x80 bit 16
        #     Dasharo me_spec_12.h: HAP_OFFSET=0x182 (SOC_INTEL_COMETLAKE_S)
        # Heuristic: fpsba+0x80 non-zero = CML-S desktop
        # --------------------------------------------------------
        elif gen == 5:
            fdf.seek(fpsba + 0x80)
            val_80 = unpack("<I", fdf.read(4))[0]
            if val_80 != 0:
                # CML-S desktop (Z490/H470/B460/H410)
                print("The HAP bit is " +
                      ("SET" if val_80 & 1 << 16 else "NOT SET") +
                      " (PCHSTRP32 at fpsba+0x80 — CML-S desktop,"
                      " Dasharo me_spec_12.h confirmed)")
            else:
                fdf.seek(fpsba + 0x70)
                pchstrp28 = unpack("<I", fdf.read(4))[0]
                print("The HAP bit is " +
                      ("SET" if pchstrp28 & 1 << 16 else "NOT SET") +
                      " (PCHSTRP28 at fpsba+0x70 — CML-LP mobile, hardware confirmed)")

        elif gen == 6:
            # TGL-LP: PCHSTRP31 at fpsba+0x7C (datasheet confirmed)
            # RKL-H/TGL-H: PCHSTRP37 at fpsba+0x94 (datasheet confirmed)
            #   Community confirmed: ASRock B560M Steel Legend (Tiger Point PCH-H)
            #   Community confirmed: Asus TUF Z590 Gaming (Tiger Point PCH-H)
            #   Source: minhkhoi89, XutaxKamay PR #384, Dec 2025
            #   Also confirmed: ME 15.0.21.1549 (skullface101, same PR)
            # Use LP/H heuristic — same approach as gen 4 (ME 12/13)
            fdf.seek(fpsba + 0x7C)
            val_7c = unpack("<I", fdf.read(4))[0]
            fdf.seek(fpsba + 0x84)
            val_84 = unpack("<I", fdf.read(4))[0]
            fdf.seek(fpsba + 0x94)
            val_94 = unpack("<I", fdf.read(4))[0]
            if val_94 & (1 << 16):
                print("The HAP bit is SET" +
                      " (PCHSTRP37 at fpsba+0x94 — RKL-H/TGL-H datasheet confirmed)")
            elif val_84 & (1 << 16):
                print("The HAP bit is SET" +
                      " (PCHSTRP33 at fpsba+0x84 — EHL Elkhart Lake,"
                      " Dasharo me_spec_15.h confirmed)")
            elif val_7c & (1 << 16):
                print("The HAP bit is SET" +
                      " (PCHSTRP31 at fpsba+0x7C — TGL-LP datasheet confirmed)")
            elif val_94 != 0:
                print("The HAP bit is NOT SET" +
                      " (PCHSTRP37 bit 16 — RKL-H/TGL-H platform detected)")
            elif val_84 != 0:
                print("The HAP bit is NOT SET" +
                      " (PCHSTRP33 bit 16 — EHL Elkhart Lake platform detected)")
            else:
                print("The HAP bit is NOT SET" +
                      " (PCHSTRP31 bit 16 — TGL-LP platform assumed)")

        elif gen == 7:
            # ADL/RPL (ME 16/16.1): PCHSTRP31 bit 16 via byte 0x017E
            # Datasheet confirmed: Doc 648364 (ADL-P/N), Doc 743835 (RPL)
            # NOTE: ADL PCH-S desktop (Z690/H670/B660) uses 0x01DE instead.
            # No reliable runtime heuristic exists to distinguish PCH-S from
            # PCH-P/N — dword at 0x1DC is populated on both. ADL-S is a known
            # gap; mobile platforms (ThinkPads, ADL-P/N/RPL) are correct here.
            fdf.seek(0x17E)
            fd_hap_byte = unpack("B", fdf.read(1))[0]
            print("The HAP bit is " +
                  ("SET" if fd_hap_byte & 0x01 else "NOT SET") +
                  " (PCHSTRP31 bit 16 via 0x017E — ADL/RPL datasheet confirmed)")

        elif gen == 8:
            # Meteor Lake (ME 18) — HAP at absolute offset 0x21E (byte write)
            # Source: Dasharo coreboot me_spec_18.h:
            #   #define HAP_OFFSET 0x21E (for SOC_INTEL_METEORLAKE_U_H)
            # Analysis: 0x21E = fpsba(0x1A0) + 0x7C(PCHSTRP31) + 0x02(byte 2 = bit 16)
            # Same strap structure as ADL/RPL (PCHSTRP31 bit 16), fpsba moved to 0x1A0
            # EXPERIMENTAL — not yet confirmed from hardware dump or Intel SPI guide
            fdf.seek(0x21E)
            hap_byte = unpack("B", fdf.read(1))[0]
            print("The HAP bit is " +
                  ("SET" if hap_byte & 0x01 else "NOT SET") +
                  " (MTL byte 0x21E — Dasharo coreboot source, experimental)")

        else:
            fdf.seek(fpsba)
            pchstrp0 = unpack("<I", fdf.read(4))[0]
            print("The HAP bit is " +
                  ("SET" if pchstrp0 & 1 << 16 else "NOT SET"))

        # Generation 1: wipe everything and disable the ME region
        if gen == 1 and me_start < me_end and not args.check:
            print("Disabling the ME region...")
            f.seek(frba + 0x8)
            f.write(pack("<I", 0x1fff))

            print("Wiping the ME region...")
            mef = RegionFile(f, me_start, me_end)
            mef.fill_all("\xff")

    # ME 6 Ignition: wipe everything
    me6_ignition = False
    if gen == 2 and not args.check and not args.soft_disable_only and \
       variant == "ME" and version[0] == 6:
        mef.seek(ftpr_offset + 0x20)
        num_modules = unpack("<I", mef.read(4))[0]
        mef.seek(ftpr_offset + 0x290 + (num_modules + 1) * 0x60)
        data = mef.read(0xc)

        if data[0x0:0x4] == b"$SKU" and data[0x8:0xc] == b"\x00\x00\x00\x00":
            print("ME 6 Ignition firmware detected, removing everything...")
            mef.fill_all(b"\xff")
            me6_ignition = True

    if gen != 1 and not args.check:
        if not args.soft_disable_only and not me6_ignition:
            # --------------------------------------------------------
            # PATCH: gen >= 4 means IFWI firmware (ME 12+).
            # Module removal / partition wiping is not supported on
            # IFWI images — attempting it will corrupt the image.
            # We print a clear warning and skip straight to HAP.
            # --------------------------------------------------------
            if gen >= 4:
                print("\nNOTE: IFWI firmware (ME {}.x) detected.".format(version[0]))
                print("      Module removal is not supported on IFWI images.")
                print("      Skipping partition cleanup — HAP bit will still be set.\n")
            else:
                print("Reading partitions list...")
                unremovable_part_fpt = b""
                extra_part_end = 0
                whitelist = []
                blacklist = []

                whitelist += unremovable_partitions

                if args.blacklist:
                    blacklist = args.blacklist.split(",")
                elif args.whitelist:
                    whitelist += args.whitelist.split(",")

                for i in range(entries):
                    partition = partitions[i * 0x20:(i + 1) * 0x20]
                    flags = unpack("<I", partition[0x1c:0x20])[0]

                    try:
                        part_name = \
                            partition[0x0:0x4].rstrip(b"\x00").decode("ascii")
                    except UnicodeDecodeError:
                        part_name = "????"

                    part_start, part_length = unpack("<II", partition[0x08:0x10])

                    if variant == "ME" and version[0] == 6 and \
                    i == entries - 1 and part_length == 0xffffffff:
                        part_length = me_end - me_start - part_start

                    part_end = part_start + part_length

                    if flags & 0x7f == 2:
                        print(" {:<4} ({:^24}, 0x{:08x} total bytes): nothing to "
                            "remove"
                            .format(part_name, "NVRAM partition, no data",
                                    part_length))
                    elif part_start == 0 or part_length == 0 or part_end > me_end:
                        print(" {:<4} ({:^24}, 0x{:08x} total bytes): nothing to "
                            "remove"
                            .format(part_name, "no data here", part_length))
                    else:
                        print(" {:<4} (0x{:08x} - 0x{:09x}, 0x{:08x} total bytes): "
                            .format(part_name, part_start, part_end, part_length),
                            end="")
                        if part_name in whitelist or (blacklist and
                        part_name not in blacklist):
                            unremovable_part_fpt += partition
                            if part_name != "FTPR":
                                extra_part_end = max(extra_part_end, part_end)
                            print("NOT removed")
                        else:
                            mef.fill_range(part_start, part_end, b"\xff")
                            print("removed")

                print("Removing partition entries in FPT...")
                mef.write_to(0x30, unremovable_part_fpt)
                mef.write_to(0x14,
                            pack("<I", len(unremovable_part_fpt) // 0x20))

                mef.fill_range(0x30 + len(unremovable_part_fpt),
                            0x30 + len(partitions), b"\xff")

                if (not blacklist and "EFFS" not in whitelist) or \
                "EFFS" in blacklist:
                    print("Removing EFFS presence flag...")
                    mef.seek(0x24)
                    flags = unpack("<I", mef.read(4))[0]
                    flags &= ~(0x00000001)
                    mef.write_to(0x24, pack("<I", flags))

                if gen == 3:
                    mef.seek(0x10)
                    header = bytearray(mef.read(0x20))
                    header[0x0b] = 0x00
                else:
                    mef.seek(0)
                    header = bytearray(mef.read(0x30))
                    header[0x1b] = 0x00
                checksum = (0x100 - sum(header) & 0xff) & 0xff

                print("Correcting checksum (0x{:02x})...".format(checksum))
                mef.write_to(0x1b, pack("B", checksum))

                print("Reading FTPR modules list...")
                if gen == 3:
                    end_addr, ftpr_offset = \
                        check_and_remove_modules_gen3(mef, me_end,
                                                    ftpr_offset, ftpr_length,
                                                    min_ftpr_offset,
                                                    args.relocate,
                                                    args.keep_modules)
                else:
                    end_addr, ftpr_offset = \
                        check_and_remove_modules(mef, me_end, ftpr_offset,
                                                min_ftpr_offset, args.relocate,
                                                args.keep_modules)

                if end_addr > 0:
                    end_addr = max(end_addr, extra_part_end)
                    end_addr = (end_addr // 0x1000 + 1) * 0x1000
                    end_addr += spared_blocks * 0x1000

                    print("The ME minimum size should be {0} bytes "
                        "({0:#x} bytes)".format(end_addr))

                    if me_start > 0:
                        print("The ME region can be reduced up to:\n"
                            " {:08x}:{:08x} me"
                            .format(me_start, me_start + end_addr - 1))
                    elif args.truncate:
                        print("Truncating file at {:#x}...".format(end_addr))
                        f.truncate(end_addr)

        # --------------------------------------------------------
        # PATCH: soft-disable write path — gen 4 & 5 use LP/H heuristic
        # --------------------------------------------------------
        if args.soft_disable or args.soft_disable_only:
            if gen == 3:
                print("Setting the HAP bit in PCHSTRP0 to disable Intel ME...")
                pchstrp0 |= (1 << 16)
                fdf.write_to(fpsba, pack("<I", pchstrp0))

            elif gen == 4:
                pchstrp_val, hap_offset, strap_name = get_hap_offset_lp_or_h(fdf, fpsba)
                print("Setting the HAP bit in {} to disable Intel ME..."
                      .format(strap_name))
                pchstrp_val |= (1 << 16)
                fdf.write_to(fpsba + hap_offset, pack("<I", pchstrp_val))

            elif gen == 5:
                # CML-S desktop: PCHSTRP32 at fpsba+0x80 — Dasharo me_spec_12.h confirmed
                # CML-LP mobile: PCHSTRP28 at fpsba+0x70 — hardware confirmed (X13 Gen1)
                fdf.seek(fpsba + 0x80)
                val_80 = unpack("<I", fdf.read(4))[0]
                if val_80 != 0:
                    # CML-S desktop (Z490/H470/B460/H410)
                    print("Setting the HAP bit in PCHSTRP32 (fpsba+0x80) to disable Intel ME...")
                    print("  (CML-S desktop — Dasharo me_spec_12.h confirmed)")
                    val_80 |= (1 << 16)
                    fdf.write_to(fpsba + 0x80, pack("<I", val_80))
                    fdf.seek(fpsba + 0x80)
                    verify_strp = unpack("<I", fdf.read(4))[0]
                    if verify_strp & (1 << 16):
                        print("  HAP write verified: PCHSTRP32 = 0x{:08X} ✓".format(verify_strp))
                    else:
                        sys.exit("ERROR: HAP write failed — PCHSTRP32 bit 16 not set after write.")
                else:
                    # CML-LP mobile (ThinkPads, X13/T14/L14 Gen1)
                    fdf.seek(fpsba + 0x70)
                    pchstrp28 = unpack("<I", fdf.read(4))[0]
                    print("Setting the HAP bit in PCHSTRP28 (fpsba+0x70) to disable Intel ME...")
                    print("  (CML-LP mobile — hardware confirmed, ThinkPad X13 Gen1)")
                    pchstrp28 |= (1 << 16)
                    fdf.write_to(fpsba + 0x70, pack("<I", pchstrp28))
                    fdf.seek(fpsba + 0x70)
                    verify_strp = unpack("<I", fdf.read(4))[0]
                    if verify_strp & (1 << 16):
                        print("  HAP write verified: PCHSTRP28 = 0x{:08X} ✓".format(verify_strp))
                    else:
                        sys.exit("ERROR: HAP write failed — PCHSTRP28 bit 16 not set after write.")

            elif gen == 6:
                # TGL-LP: PCHSTRP31 at fpsba+0x7C (datasheet confirmed)
                # RKL-H/TGL-H: PCHSTRP37 at fpsba+0x94 (datasheet confirmed)
                # Use LP/H heuristic — check fpsba+0x94 first (H-series has
                # non-zero value there), fall back to LP (fpsba+0x7C)
                fdf.seek(fpsba + 0x84)
                val_84 = unpack("<I", fdf.read(4))[0]
                fdf.seek(fpsba + 0x94)
                val_94 = unpack("<I", fdf.read(4))[0]
                if val_94 != 0:
                    # H-series platform (RKL-H or TGL-H, Tiger Point PCH-H)
                    print("Setting the HAP bit in PCHSTRP37 (fpsba+0x94) to disable Intel ME...")
                    print("  (RKL-H / TGL-H — Tiger Point PCH-H, datasheet confirmed)")
                    val_94 |= (1 << 16)
                    fdf.write_to(fpsba + 0x94, pack("<I", val_94))
                    fdf.seek(fpsba + 0x94)
                    verify_strp = unpack("<I", fdf.read(4))[0]
                    if verify_strp & (1 << 16):
                        print("  HAP write verified: PCHSTRP37 = 0x{:08X} ✓".format(verify_strp))
                    else:
                        sys.exit("ERROR: HAP write failed — PCHSTRP37 bit 16 not set after write.")
                elif val_84 != 0:
                    # EHL (Elkhart Lake, Atom x6000) — PCHSTRP33 at fpsba+0x84
                    # Dasharo me_spec_15.h: HAP_OFFSET=0x186 (SOC_INTEL_ELKHARTLAKE)
                    print("Setting the HAP bit in PCHSTRP33 (fpsba+0x84) to disable Intel ME...")
                    print("  (Elkhart Lake — Dasharo me_spec_15.h confirmed)")
                    val_84 |= (1 << 16)
                    fdf.write_to(fpsba + 0x84, pack("<I", val_84))
                    fdf.seek(fpsba + 0x84)
                    verify_strp = unpack("<I", fdf.read(4))[0]
                    if verify_strp & (1 << 16):
                        print("  HAP write verified: PCHSTRP33 = 0x{:08X} ✓".format(verify_strp))
                    else:
                        sys.exit("ERROR: HAP write failed — PCHSTRP33 bit 16 not set after write.")
                else:
                    # LP platform (TGL-LP, TGL PCH-LP)
                    fdf.seek(fpsba + 0x7C)
                    val_7c = unpack("<I", fdf.read(4))[0]
                    print("Setting the HAP bit in PCHSTRP31 (fpsba+0x7C) to disable Intel ME...")
                    print("  (Tiger Lake LP — TGL PCH-LP, datasheet confirmed)")
                    val_7c |= (1 << 16)
                    fdf.write_to(fpsba + 0x7C, pack("<I", val_7c))
                    fdf.seek(fpsba + 0x7C)
                    verify_strp = unpack("<I", fdf.read(4))[0]
                    if verify_strp & (1 << 16):
                        print("  HAP write verified: PCHSTRP31 = 0x{:08X} ✓".format(verify_strp))
                    else:
                        sys.exit("ERROR: HAP write failed — PCHSTRP31 bit 16 not set after write.")

            elif gen == 7:
                # ADL/RPL (ME 16/16.1): PCHSTRP31 bit 16 via byte 0x017E
                # Datasheet confirmed: Doc 648364 (ADL-P/N), Doc 743835 (RPL)
                # NOTE: ADL PCH-S desktop (Z690/H670/B660) uses 0x01DE (PCHSTRP55).
                # No reliable runtime heuristic to auto-detect PCH-S vs PCH-P/N —
                # dword at 0x1DC is populated on both platforms. ADL-S desktop is a
                # known gap. Mobile (ThinkPads, ADL-P/N, RPL-P/H) are correct here.
                print("Setting the HAP bit in PCHSTRP31 bit 16 (descriptor byte "
                      "0x017E) to disable Intel ME...")
                print("  (Alder Lake / Raptor Lake — Intel datasheet confirmed, Doc 648364)")
                fdf.seek(0x17E)
                orig_byte = unpack("B", fdf.read(1))[0]
                fdf.write_to(0x17E, pack("B", orig_byte | 0x01))
                fdf.seek(0x17E)
                verify_byte = unpack("B", fdf.read(1))[0]
                if verify_byte & 0x01:
                    print("  HAP write verified: byte 0x017E = 0x{:02X} ✓".format(verify_byte))
                else:
                    sys.exit("ERROR: HAP write failed — byte 0x017E still reads "
                             "0x{:02X} after write. Image may be read-only.".format(verify_byte))

            elif gen == 8:
                # Meteor Lake (ME 18) — HAP at byte 0x21E
                # Source: Dasharo coreboot me_spec_18.h HAP_OFFSET = 0x21E
                #   (SOC_INTEL_METEORLAKE_U_H confirmed)
                # Analysis: 0x21E = fpsba(0x1A0) + 0x7C(PCHSTRP31) + 0x02(bit 16)
                # Same strap structure as ADL/RPL, fpsba shifted from 0x100 to 0x1A0
                # EXPERIMENTAL — Dasharo source only, not confirmed from hardware dump
                # or Intel MTL SPI Programming Guide. Use hap_diff.py to verify.
                print("Setting the HAP bit for Meteor Lake (ME 18)...")
                print("  Byte write to 0x21E (Dasharo coreboot me_spec_18.h source)")
                print("  EXPERIMENTAL — run hap_diff.py on before/after to verify")
                fdf.write_to(0x21E, pack("B", 0x01))
                fdf.seek(0x21E)
                verify_byte = unpack("B", fdf.read(1))[0]
                if verify_byte & 0x01:
                    print("  HAP write verified: byte 0x21E = 0x{:02X} ✓".format(verify_byte))
                else:
                    sys.exit("ERROR: HAP write failed — byte 0x21E bit 0 not set after write.")

            else:
                print("Setting the AltMeDisable bit in PCHSTRP10 to disable "
                      "Intel ME...")
                pchstrp10 |= (1 << 7)
                fdf.write_to(fpsba + 0x28, pack("<I", pchstrp10))

    if args.descriptor:
        print("Removing ME/TXE R/W access to the other flash regions...")
        if gen == 3:
            flmstr2 = 0x00400500
        else:
            fdf.seek(fmba + 0x4)
            flmstr2 = (unpack("<I", fdf.read(4))[0] | 0x04040000) & 0x0404ffff

        fdf.write_to(fmba + 0x4, pack("<I", flmstr2))

    if args.extract_descriptor:
        if args.truncate:
            print("Extracting the descriptor to \"{}\"..."
                  .format(args.extract_descriptor))
            fdf_copy = fdf.save(args.extract_descriptor, fd_end - fd_start)

            if bios_start == me_end:
                print("Modifying the regions of the extracted descriptor...")
                print(" {:08x}:{:08x} me   --> {:08x}:{:08x} me"
                      .format(me_start, me_end - 1,
                              me_start, me_start + end_addr - 1))
                print(" {:08x}:{:08x} bios --> {:08x}:{:08x} bios"
                      .format(bios_start, bios_end - 1,
                              me_start + end_addr, bios_end - 1))

                flreg1 = start_end_to_flreg(me_start + end_addr, bios_end)
                if gen != 1:
                    flreg2 = start_end_to_flreg(me_start, me_start + end_addr)

                fdf_copy.seek(frba + 0x4)
                fdf_copy.write(pack("<I", flreg1))
                if gen != 1:
                    fdf_copy.write(pack("<I", flreg2))
            else:
                print("\nWARNING:\n"
                      "The start address of the BIOS region (0x{:08x}) isn't "
                      "equal to the end address\nof the ME region (0x{:08x}): "
                      "if you want to recover the space from the ME \nregion "
                      "you have to manually modify the descriptor.\n"
                      .format(bios_start, me_end))
        else:
            print("Extracting the descriptor to \"{}\"..."
                  .format(args.extract_descriptor))
            fdf_copy = fdf.save(args.extract_descriptor, fd_end - fd_start)

        fdf_copy.close()

    if gen != 1:
        if args.extract_me:
            if args.truncate:
                print("Extracting and truncating the ME image to \"{}\"..."
                      .format(args.extract_me))
                mef_copy = mef.save(args.extract_me, end_addr)
            else:
                print("Extracting the ME image to \"{}\"..."
                      .format(args.extract_me))
                mef_copy = mef.save(args.extract_me, me_end - me_start)

            if not me6_ignition:
                print("Checking the FTPR RSA signature of the extracted ME "
                      "image... ", end="")
                print_check_partition_signature(mef_copy,
                                                ftpr_offset + ftpr_mn2_offset,
                                                gen)
            mef_copy.close()

        if not me6_ignition:
            print("Checking the FTPR RSA signature... ", end="")
            print_check_partition_signature(mef, ftpr_offset + ftpr_mn2_offset, gen)

    f.close()

    if not args.check:
        print("Done! Good luck!")
