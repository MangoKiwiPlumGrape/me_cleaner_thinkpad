#!/usr/bin/env python3
# hap_diff.py — HAP bit finder for stock.bin vs FIT-patched firmware with Reserved=YES 
#
# Handles FIT output which changes many bytes (checksums, version counters,
# provisioning blocks etc). Isolates the HAP bit change from the noise.
#
# Usage:
#   python3 hap_diff.py stock.bin patched.bin
#
# What it does:
#   1. Counts all differences
#   2. Reads fpsba from the flash descriptor
#   3. Scans ONLY the descriptor strap region for changes
#   4. Identifies single-bit changes (HAP candidates)
#   5. Ignores changes outside the strap region (FIT noise)
#   6. Confirms if bit 16 of a PCHSTRP changed (the HAP bit pattern)
#
# Requirements: python3 only — no external tools needed

import sys
import struct

RED   = '\033[0;31m'
GRN   = '\033[0;32m'
YEL   = '\033[1;33m'
CYN   = '\033[0;36m'
BLD   = '\033[1m'
RST   = '\033[0m'

def banner(text):
    w = 52
    print(f"\n{BLD}{'═'*w}{RST}")
    print(f"{BLD}  {text}{RST}")
    print(f"{BLD}{'═'*w}{RST}\n")

def section(text):
    print(f"{BLD}─── {text} ───{RST}\n")

if len(sys.argv) != 3:
    print(f"Usage: python3 hap_diff.py stock.bin patched.bin")
    sys.exit(1)

stock_path   = sys.argv[1]
patched_path = sys.argv[2]

with open(stock_path,   'rb') as f: stock   = f.read()
with open(patched_path, 'rb') as f: patched = f.read()

banner("HAP Bit Finder — hap_diff.py")
print(f"  Stock  : {CYN}{stock_path}{RST}  ({len(stock):,} bytes)")
print(f"  Patched: {CYN}{patched_path}{RST}  ({len(patched):,} bytes)")

if len(stock) != len(patched):
    print(f"\n{YEL}  Warning: different sizes ({len(stock):,} vs {len(patched):,} bytes){RST}")
    print(f"{YEL}  Comparison covers the smaller file only.{RST}")

compare_len = min(len(stock), len(patched))

# ── Count ALL differences ──────────────────────────────────────────────────
all_diffs = [(i, stock[i], patched[i])
             for i in range(compare_len) if stock[i] != patched[i]]

print(f"\n  Total bytes changed: {BLD}{GRN}{len(all_diffs)}{RST}")

if not all_diffs:
    print(f"\n{YEL}  Files are identical.{RST}")
    sys.exit(0)

# ── Parse flash descriptor ─────────────────────────────────────────────────
print()
section("Flash Descriptor")

is_full_dump = stock[0:4] == b'\x5a\xa5\xf0\x0f'

if not is_full_dump:
    # Try offset 0x10 (ME-only extract with FPT header)
    print(f"  {YEL}No descriptor signature at offset 0 — not a full SPI dump.{RST}")
    print(f"  {YEL}Cannot determine fpsba. HAP analysis requires a full dump.{RST}")
    print(f"  {YEL}Falling back to showing all diffs.{RST}\n")

    # Just show diffs grouped by region
    section("All differences (grouped by proximity)")
    prev_off = -100
    for off, sb, pb in all_diffs:
        if off - prev_off > 0x100:
            print(f"  --- new region around {hex(off)} ---")
        dword_off = off & ~3
        s_dw = struct.unpack_from('<I', stock,   dword_off)[0] if dword_off+4 <= len(stock)   else 0
        p_dw = struct.unpack_from('<I', patched, dword_off)[0] if dword_off+4 <= len(patched) else 0
        xor  = s_dw ^ p_dw
        bits = [i for i in range(32) if (xor >> i) & 1]
        marker = f" {GRN}← single-bit change! bit {bits[0]}{RST}" if len(bits)==1 else ""
        print(f"  0x{off:06X}: {sb:02X} → {pb:02X}  (DWORD {hex(s_dw)} → {hex(p_dw)} XOR {hex(xor)}){marker}")
        prev_off = off
    sys.exit(0)

# Full SPI dump — parse descriptor
desc_off = 0x04  # descriptor starts at byte 4 after signature
flmap0 = struct.unpack_from('<I', stock, 0x04)[0]
flmap1 = struct.unpack_from('<I', stock, 0x08)[0]
flmap2 = struct.unpack_from('<I', stock, 0x0C)[0]

frba  = ((flmap0 >> 16) & 0xFF) << 4
fpsba = ((flmap1 >> 16) & 0xFF) << 4
fmba  = (flmap1 & 0xFF) << 4

print(f"  FRBA   : {hex(frba)}")
print(f"  FPSBA  : {hex(fpsba)}")
print(f"  FMBA   : {hex(fmba)}")

# Determine descriptor strap region size
# Read FLMAP1 NM field (bits 11:8) — number of PCH straps
nm = (flmap1 >> 8) & 0xF
strap_region_size = nm * 4 * 4  # NM * 4 straps per entry * 4 bytes
# In practice, strap region extends well beyond NM — use generous bound
strap_region_end = fpsba + 0x200  # 128 PCHSTRP dwords = 512 bytes

print(f"  NM     : {nm} (strap groups)")
print(f"  Strap region: {hex(fpsba)} – {hex(strap_region_end)}")

# Also check for IOE soft straps (MTL+) around 0xCAC
ioe_strap_start = 0xC00
ioe_strap_end   = 0xE00

# ── Categorise all differences ─────────────────────────────────────────────
print()
section("Categorising differences")

desc_diffs    = []   # changes in flash descriptor region (0x000–0xFFF)
strap_diffs   = []   # changes specifically in PCH strap region
ioe_diffs     = []   # changes in IOE soft strap region (MTL+)
me_diffs      = []   # changes in ME firmware region
bios_diffs    = []   # changes in BIOS region
other_diffs   = []   # everything else

# Read region map
def region_bounds(stock_data, frba_off, idx):
    flreg = struct.unpack_from('<I', stock_data, frba_off + idx*4)[0]
    base  = (flreg & 0x7FFF) << 12
    limit = ((flreg >> 16) & 0x7FFF) << 12
    if limit < base:
        return None, None  # unused
    return base, limit + 0xFFF

fd_base,   fd_end   = 0x000000, 0x000FFF
me_base,   me_end   = region_bounds(stock, frba, 2)
bios_base, bios_end = region_bounds(stock, frba, 1)

for off, sb, pb in all_diffs:
    if fpsba <= off < strap_region_end:
        strap_diffs.append((off, sb, pb))
    elif ioe_strap_start <= off < ioe_strap_end:
        ioe_diffs.append((off, sb, pb))
    elif fd_base <= off <= fd_end:
        desc_diffs.append((off, sb, pb))
    elif me_base and me_base <= off <= me_end:
        me_diffs.append((off, sb, pb))
    elif bios_base and bios_base <= off <= bios_end:
        bios_diffs.append((off, sb, pb))
    else:
        other_diffs.append((off, sb, pb))

print(f"  PCH strap region ({hex(fpsba)}–{hex(strap_region_end)}): "
      f"{BLD}{GRN if strap_diffs else YEL}{len(strap_diffs)}{RST} changes")
print(f"  IOE strap region ({hex(ioe_strap_start)}–{hex(ioe_strap_end)}): "
      f"{BLD}{GRN if ioe_diffs else ''}{len(ioe_diffs)}{RST} changes  ← MTL+ HAP candidate")
print(f"  Other descriptor :  {len(desc_diffs)} changes  (version/checksum noise)")
print(f"  ME firmware      :  {len(me_diffs)} changes  (FIT provisioning/version noise)")
print(f"  BIOS region      :  {len(bios_diffs)} changes")
print(f"  Other            :  {len(other_diffs)} changes")

# ── PCH strap analysis ─────────────────────────────────────────────────────
if strap_diffs:
    print()
    section("PCH strap region changes (HAP candidates)")

    seen_dwords = set()
    for off, sb, pb in strap_diffs:
        dword_off = off & ~3
        if dword_off in seen_dwords:
            continue
        seen_dwords.add(dword_off)

        s_dw = struct.unpack_from('<I', stock,   dword_off)[0]
        p_dw = struct.unpack_from('<I', patched, dword_off)[0]
        xor  = s_dw ^ p_dw
        bits = [i for i in range(32) if (xor >> i) & 1]
        rel  = dword_off - fpsba
        strp = rel // 4

        print(f"  PCHSTRP{strp:<3} at {hex(dword_off)} (fpsba+{hex(rel)}):")
        print(f"    Stock  : {hex(s_dw):>12}  ({s_dw:032b})")
        print(f"    Patched: {hex(p_dw):>12}  ({p_dw:032b})")
        print(f"    XOR    : {hex(xor):>12}  bits changed: {bits}")

        if bits == [16]:
            print(f"    {GRN}{BLD}✓ BIT 16 ONLY — THIS IS THE HAP BIT{RST}")
            print(f"    {GRN}{BLD}✓ HAP location: fpsba + {hex(rel)} = PCHSTRP{strp} bit 16{RST}")
            print(f"    {GRN}{BLD}✓ Descriptor byte: {hex(dword_off + 2)} (byte write target){RST}")
        elif 16 in bits:
            print(f"    {YEL}⚠ Bit 16 changed but so did other bits — check carefully{RST}")
        else:
            print(f"    (bit 16 not involved — likely not HAP)")
        print()

# ── IOE strap analysis (MTL+) ─────────────────────────────────────────────
if ioe_diffs:
    print()
    section("IOE soft strap region changes (MTL+ HAP candidates)")

    seen_dwords = set()
    for off, sb, pb in ioe_diffs:
        dword_off = off & ~3
        if dword_off in seen_dwords:
            continue
        seen_dwords.add(dword_off)

        s_dw = struct.unpack_from('<I', stock,   dword_off)[0]
        p_dw = struct.unpack_from('<I', patched, dword_off)[0]
        xor  = s_dw ^ p_dw
        bits = [i for i in range(32) if (xor >> i) & 1]

        print(f"  IOE strap at {hex(dword_off)}:")
        print(f"    Stock  : {hex(s_dw):>12}  ({s_dw:032b})")
        print(f"    Patched: {hex(p_dw):>12}  ({p_dw:032b})")
        print(f"    XOR    : {hex(xor):>12}  bits changed: {bits}")

        if bits == [16]:
            print(f"    {GRN}{BLD}✓ BIT 16 ONLY — THIS IS THE HAP BIT (MTL+ IOE strap){RST}")
            print(f"    {GRN}{BLD}✓ HAP location: absolute offset {hex(dword_off)}{RST}")
            print(f"    {GRN}{BLD}✓ Byte write target: {hex(dword_off + 2)}{RST}")
        elif 16 in bits:
            print(f"    {YEL}⚠ Bit 16 changed along with others{RST}")
        else:
            print(f"    (bit 16 not involved)")
        print()

# ── Summary of FIT noise (just counts, not full dump) ─────────────────────
if me_diffs or desc_diffs:
    print()
    section("FIT noise summary (ignored for HAP analysis)")
    if desc_diffs:
        print(f"  {len(desc_diffs)} descriptor changes (version counters, checksums)")
    if me_diffs:
        # Group by proximity
        regions = []
        start = me_diffs[0][0]
        end   = me_diffs[0][0]
        for off, _, _ in me_diffs[1:]:
            if off - end < 0x100:
                end = off
            else:
                regions.append((start, end))
                start = end = off
        regions.append((start, end))
        print(f"  {len(me_diffs)} ME region changes in {len(regions)} cluster(s):")
        for s, e in regions:
            size = e - s + 1
            print(f"    {hex(s)}–{hex(e)}  ({size} bytes)  "
                  f"← FIT provisioning/version/checksum noise")

# ── Final verdict ──────────────────────────────────────────────────────────
print()
banner("Result")

hap_confirmed = False
for off, sb, pb in strap_diffs:
    dword_off = off & ~3
    s_dw = struct.unpack_from('<I', stock,   dword_off)[0]
    p_dw = struct.unpack_from('<I', patched, dword_off)[0]
    xor  = s_dw ^ p_dw
    bits = [i for i in range(32) if (xor >> i) & 1]
    if bits == [16]:
        rel  = (dword_off - fpsba)
        strp = rel // 4
        print(f"  {GRN}{BLD}HAP CONFIRMED — PCHSTRP{strp} bit 16{RST}")
        print(f"  {GRN}fpsba + {hex(rel)} = absolute {hex(dword_off)}{RST}")
        print(f"  {GRN}Byte write: {hex(dword_off + 2)}{RST}")
        print(f"\n  Add to me_cleaner gen mapping:")
        print(f"    ME_VERSION_MAP[XX] = <new gen>")
        print(f"  Add HAP write:")
        print(f"    fdf.seek({hex(fpsba + rel)})")
        print(f"    pchstrp = unpack('<I', fdf.read(4))[0]")
        print(f"    pchstrp |= (1 << 16)")
        print(f"    fdf.write_to({hex(fpsba + rel)}, pack('<I', pchstrp))")
        hap_confirmed = True
        break

for off, sb, pb in ioe_diffs:
    dword_off = off & ~3
    s_dw = struct.unpack_from('<I', stock,   dword_off)[0]
    p_dw = struct.unpack_from('<I', patched, dword_off)[0]
    xor  = s_dw ^ p_dw
    bits = [i for i in range(32) if (xor >> i) & 1]
    if bits == [16]:
        print(f"  {GRN}{BLD}HAP CONFIRMED — IOE soft strap bit 16 (MTL+ platform){RST}")
        print(f"  {GRN}Absolute offset: {hex(dword_off)}{RST}")
        print(f"  {GRN}Byte write target: {hex(dword_off + 2)}{RST}")
        print(f"\n  Add to me_cleaner gen 8 write block:")
        print(f"    fdf.seek({hex(dword_off)})")
        print(f"    ioe_strap = unpack('<I', fdf.read(4))[0]")
        print(f"    ioe_strap |= (1 << 16)")
        print(f"    fdf.write_to({hex(dword_off)}, pack('<I', ioe_strap))")
        hap_confirmed = True
        break

if not hap_confirmed:
    if not strap_diffs and not ioe_diffs:
        print(f"  {YEL}No changes found in PCH strap or IOE strap regions.{RST}")
        print(f"  {YEL}HAP bit location not determined from this diff.{RST}")
        print(f"  {YEL}Possible causes:{RST}")
        print(f"    - HAP was already set in the stock image")
        print(f"    - FIT used a different descriptor layout")
        print(f"    - Files are from different firmware versions")
    else:
        print(f"  {YEL}Strap region changes found but bit 16 pattern not confirmed.{RST}")
        print(f"  {YEL}Review the strap changes above manually.{RST}")

print()
