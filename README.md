<div align="center">

# me_cleaner v1.3 — HAP / Soft-Disable Fork
### Hardware-confirmed Intel ME disable for 8th–14th Gen Intel platforms

[![ME 12](https://img.shields.io/badge/ME%2012-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 13](https://img.shields.io/badge/ME%2013-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 14](https://img.shields.io/badge/ME%2014-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 15](https://img.shields.io/badge/ME%2015-experimental-orange?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad/tree/main/experimental)
[![ME 16](https://img.shields.io/badge/ME%2016-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad/tree/main/experimental)
[![ME 18](https://img.shields.io/badge/ME%2018-unconfirmed-red?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad/tree/main/experimental)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](https://www.gnu.org/licenses/gpl-3.0)
[![Fork of](https://img.shields.io/badge/fork%20of-corna%2Fme__cleaner-lightgrey?style=flat-square)](https://github.com/corna/me_cleaner)
[![Hardware Tested](https://img.shields.io/badge/hardware-tested%20%26%20flashed-success?style=flat-square)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![Year](https://img.shields.io/badge/updated-2026-informational?style=flat-square)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

> **Fork of [corna/me_cleaner](https://github.com/corna/me_cleaner) fixing HAP bit offsets for 8th–13th gen Intel platforms, with datasheet-confirmed support for Alder Lake / Raptor Lake (ME 16/16.1) and a placeholder for Meteor Lake (ME 18). All stable fixes hardware-confirmed on real hardware.**

</div>

> **Experimental support for ME 15–18 (Tiger Lake, Alder Lake, Raptor Lake, Meteor Lake) is in [experimental/](experimental/).**
> ME 16/16.1 (ADL/RPL) is now datasheet-confirmed. ME 18 (MTL) is a placeholder — HAP path unconfirmed. Reports welcome.

---

For a detailed comparison of HAP vs soft-disable effectiveness across hardware generations, see [ME_Disable_Comparison.md](ME_Disable_Comparison.md).

---

## What This Fork Fixes

The original me_cleaner v1.2 has two problems on modern platforms:

**Problem 1 — ME 14 (10th gen, Comet Lake LP) writes to the wrong strap.**
The original hardcodes `fpsba+0x80` (PCHSTRP32) for ME 14. On Comet Lake LP (ThinkPad X13, T14, L14 Gen1 etc.) the HAP bit lives in `fpsba+0x70` (PCHSTRP28) at bit 16. Writing to `+0x80` silently does nothing.

**Problem 2 — ME 13 (Ice Lake, 10th gen) is completely missing.**
The original has no version mapping for ME 13. Ice Lake systems fall through with undefined behaviour. This fork maps ME 13 to gen 4 (`fpsba+0x70`), confirmed by Intel PCH datasheet Doc 615170.

**Additionally fixed vs all other forks:**
- ME 16/16.1 (ADL/RPL) HAP location corrected — old forks used `fpsba+0xDC` (PCHSTRP55) which is wrong. The correct location is `fpsba+0x7C` (PCHSTRP31 bit 16), confirmed by Intel 600-series PCH Datasheet (Doc 648364) and 700-series (Doc 743835). Writing to byte `0x017E` is identical — it is byte 2 of the PCHSTRP31 dword at `fpsba+0x17C`.
- ME 18 (MTL) warning added — MTL has no PCH straps at `0x100`. The current gen 7 path is a placeholder and prints a runtime warning. Do not rely on it for MTL without confirming the HAP offset from a real MTL dump first.

---

## Hardware-Confirmed HAP Bit Locations

| ME Version | Platform | ThinkPad | HAP Location | Status |
|---|---|---|---|---|
| ME 12.0.x | Coffee Lake U (8th gen) | X1 Carbon Gen 6/7 | `fpsba+0x70` PCHSTRP28 bit 16 | ✅ hardware confirmed |
| ME 12.0.x | Cannon Lake H (desktop) | Z390/H370/B360 | `fpsba+0x80` PCHSTRP32 bit 16 | ✅ confirmed via PR#282 |
| ME 13.x.x | Ice Lake LP (10th gen) | — | `fpsba+0x70` PCHSTRP28 bit 16 | ✅ datasheet confirmed (Doc 615170) |
| ME 14.1.x | Comet Lake LP (10th gen) | X13 Gen1, T14 Gen1 | `fpsba+0x70` PCHSTRP28 bit 16 | ✅ hardware confirmed |
| ME 15.x.x | Tiger Lake (11th gen) | — | `fpsba+0x7C` PCHSTRP31 bit 16 | ⚠️ community confirmed |
| ME 16.x.x | Alder Lake (12th gen) | — | `fpsba+0x7C` PCHSTRP31 bit 16 | ✅ datasheet confirmed (Doc 648364) |
| ME 16.1.x | Raptor Lake (13th gen) | — | `fpsba+0x7C` PCHSTRP31 bit 16 | ✅ datasheet confirmed (Doc 743835) |
| ME 18.x.x | Meteor Lake (14th gen) | — | Unknown — descriptor layout changed | ❌ unconfirmed, placeholder only |

**Proof for CML-U LP (ThinkPad X13 Gen1):**
```
stock   PCHSTRP28 = 0x801801b8   (HAP bit 16 = 0)
patched PCHSTRP28 = 0x801901b8   (HAP bit 16 = 1)
diff    =           0x00010000   ← exactly one bit
cmp -l byte 371 = fpsba(0x100) + 0x70 + 3 (byte 3 of dword)
```

**ADL/RPL offset clarification:**
```
fpsba         = 0x100           (confirmed, Intel 600/700-series PCH datasheets)
PCHSTRP31     = fpsba + 0x7C   = 0x17C   (the 32-bit strap dword)
byte 0x017E   = fpsba + 0x7E   = byte 2 of PCHSTRP31 = bit 16 of PCHSTRP31
```
These are NOT two different locations. Old forks used `fpsba+0xDC` (PCHSTRP55) — that is wrong.

---

## Changes vs Original me_cleaner v1.2

| Change | Original | This Fork |
|---|---|---|
| ME 14 HAP offset | `fpsba+0x80` ❌ | `fpsba+0x70` PCHSTRP28 ✅ hw confirmed |
| ME 13 (Ice Lake) | missing — undefined | gen 4, `fpsba+0x70`, datasheet confirmed |
| ME 15 (Tiger Lake) | missing | gen 6, `fpsba+0x7C` PCHSTRP31 |
| ME 16/16.1 (ADL/RPL) | missing or wrong `+0xDC` | gen 7, `fpsba+0x7C` PCHSTRP31, datasheet confirmed |
| ME 18 (MTL) | missing | gen 7 placeholder with runtime warning |
| ME 12 LP vs H | `fpsba+0x70` only | LP/H heuristic: reads both straps, picks correct one |
| IFWI warning | silent skip | explicit warning, continues to HAP |
| Version string | `1.2` | `1.3-thinkpad-fork` |

---

## Supported Platforms

This fork is focused on **soft-disable via HAP bit only** (`-s` / `-S` flags). Module removal is **not supported** on ME 12+ IFWI firmware — the script warns and skips it automatically.

| Generation | CPU | ME Version | Internal gen | HAP Path | Status |
|---|---|---|---|---|---|
| 8th gen (U) | Coffee Lake / Whiskey Lake | ME 12.0.x | gen 4 | `fpsba+0x70` PCHSTRP28 | ✅ hardware confirmed |
| 8th/9th gen (H) | Cannon Lake H | ME 12.0.x | gen 4 | `fpsba+0x80` PCHSTRP32 | ✅ confirmed via PR#282 |
| 10th gen (U) | Ice Lake LP | ME 13.x.x | gen 4 | `fpsba+0x70` PCHSTRP28 | ✅ datasheet confirmed (Doc 615170) |
| 10th gen (U) | Comet Lake LP | ME 14.1.x | gen 5 | `fpsba+0x70` PCHSTRP28 | ✅ hardware confirmed (X13 Gen1) |
| 11th gen | Tiger Lake | ME 15.x.x | gen 6 | `fpsba+0x7C` PCHSTRP31 | ⚠️ community confirmed |
| 12th gen | Alder Lake | ME 16.x.x | gen 7 | `fpsba+0x7C` PCHSTRP31 | ✅ datasheet confirmed (Doc 648364) |
| 13th gen | Raptor Lake | ME 16.1.x | gen 7 | `fpsba+0x7C` PCHSTRP31 | ✅ datasheet confirmed (Doc 743835) |
| 14th gen | Meteor Lake | ME 18.x.x | gen 7 ⚠️ | unknown | ❌ placeholder — do not rely on |

---

## MTL Warning

Meteor Lake (ME 18) uses a completely different descriptor layout. There are no PCH Straps at `0x100` on MTL. The HAP bit likely lives in IOE Soft Straps at `0xCAC`, but this has not been empirically confirmed. The current code prints a runtime warning when ME 18 is detected and still writes to `0x017E` — this write is almost certainly wrong on MTL and may have no effect. **Do not flash an MTL image based on this tool without first confirming the HAP offset from a known-good MTL dump.**

---

## Usage

```bash
# 1. Back up your BIOS first — always
sudo flashrom -p internal -r stock_backup.bin

# 2. Check current state (no writes, safe to run)
python3 me_cleaner.py -c stock_backup.bin

# 3. Set HAP bit only — writes to a new output file
python3 me_cleaner.py -s stock_backup.bin -O patched.bin

# 4. Verify before flashing
python3 me_cleaner.py -c patched.bin
# Should print: The HAP bit is SET

# 5. Flash
sudo flashrom -p internal -w patched.bin
```

---

## Verifying It Worked After Reboot

```bash
# ME should disappear from PCI bus
lspci | grep -i "mei\|management engine\|heci"
# → nothing

# If you have intelmetool-thinkpad
sudo ./intelmetool -m
# → "ME disabled" or ME version 0.0.0.0
```

---

## Requirements

- Python 3
- `flashrom` for dumping/flashing
- Root access
- A full BIOS dump (not just the ME region) — `-s` requires a full image

---

## Important Warnings

- **Always back up your BIOS before flashing.**
- This is a **firmware-level soft disable** only. ME hardware still exists — it halts itself after hardware init when HAP is set.
- This does **not** remove ME modules. On IFWI firmware (ME 12+) module removal corrupts the image.
- Tested primarily on ThinkPads. Other vendors may have different `fpsba` layouts — always run `-c` first.
- If `-c` reports HAP already SET on your stock image, do not patch — it's already disabled.

---

## What Happens After Setting HAP

| Tool | Before HAP | After HAP |
|---|---|---|
| BIOS ME version | 14.x.x.x | **blank** |
| `lspci` | MEI device visible | **nothing** |
| MEInfo | returns ME data | **nothing** |
| intelmetool | returns ME data | **nothing** |
| MEAnalyzer (file) | HAP = No | **HAP = Yes** |
| Any ME tool (live) | functional | **no device** |

---

## Deep Dive: What Intel FIT Actually Does for HAP (CML-LP Research)

A byte-level analysis was performed comparing a stock BIOS dump against an Intel FIT HAP-patched image on a 10th gen ThinkPad (Comet Lake LP, ME 14.1.x, vPro).

### The Simple Truth

**A single byte change is sufficient to set HAP and disable ME on CML-LP.**

This fork changes exactly 1 byte — `PCHSTRP28` at `fpsba+0x70`, bit 16. After flashing, ME disappears from BIOS, lspci, and all ME tools. Intel FIT changes 534 bytes for the same operation. Here is why.

### What FIT Changes Beyond the HAP Bit

**1. HAP bit — `fpsba+0x70` bit 16 (byte `0x173`)**
```
stock:   PCHSTRP28 = 0x801801b8
patched: PCHSTRP28 = 0x801901b8
diff:              = 0x00010000  ← one bit
```

**2. Descriptor metadata** — version/sequence counters updated in 3 regions (`0x4000`, `0x157000`, `0x63f000`). Same 4-byte pattern changes identically across all three.

**3. Checksums recalculated** — EFI firmware volumes and FPT header checksums updated.

**4. ME provisioning block wiped** — `0x786000`–`0x786208` (519 bytes → `0xFF`). Likely AMT provisioning tokens being invalidated.

Changes 2, 3 and 4 are **not required** for HAP to take effect. This fork proves it — ME disappears with only the single bit flip.

---

## Credits

Original me_cleaner by **Nicola Corna** — Copyright (C) 2016–2018  
License: GNU GPL v3 — https://github.com/corna/me_cleaner

ME 12 H (PCHSTRP32) findings: PR#282 by @ghost / @davidmartinzeus  
ME 15/16 HAP offsets: **XutaxKamay** — https://github.com/XutaxKamay/me_cleaner

HAP offset hardware confirmation for ME 14 CML-LP (this fork):
Verified via byte-level diff of stock vs Intel FIT-patched BIOS on ThinkPad X13 Gen1 (Comet Lake LP, ME 14.1.x)
`stock 0x801801b8 → patched 0x801901b8 — diff = 0x00010000 (bit 16 of PCHSTRP28)`

ME 16/16.1 HAP location confirmed from Intel PCH datasheets Doc 648364 (ADL) and Doc 743835 (RPL).
ME 13 HAP location confirmed from Intel PCH datasheet Doc 615170 (ICL).

---

## License

GNU General Public License v3 — see [LICENSE](LICENSE) for full terms.
You must retain the original copyright notice when distributing modified versions.
