<div align="center">

# me_cleaner v1.3 — HAP Fork

### Datasheet-confirmed Intel ME disable for 8th–15th gen Intel platforms

[![ME 12](https://img.shields.io/badge/ME%2012-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 13](https://img.shields.io/badge/ME%2013-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 14](https://img.shields.io/badge/ME%2014-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 15](https://img.shields.io/badge/ME%2015-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 16](https://img.shields.io/badge/ME%2016-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 18](https://img.shields.io/badge/ME%2018-unconfirmed-red?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](https://www.gnu.org/licenses/gpl-3.0)
[![Fork of](https://img.shields.io/badge/fork%20of-corna%2Fme__cleaner-lightgrey?style=flat-square)](https://github.com/corna/me_cleaner)
[![Hardware Tested](https://img.shields.io/badge/hardware-tested%20%26%20flashed-success?style=flat-square)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

> Fork of [corna/me_cleaner](https://github.com/corna/me_cleaner) with correct HAP bit offsets for 8th–14th gen Intel platforms. If you have used another fork and ME is still present after flashing — this is probably why.

</div>

---

## The Problem With Other Forks

The original me_cleaner v1.2 and most forks write to the wrong HAP strap on several platforms. The tool reports success, the image is modified, and ME keeps running. This is worse than doing nothing because you don't know it failed.

**What was wrong, and what this fork fixes:**

**ME 13 (Ice Lake)** was completely absent from all forks. The tool would exit with an error on ICL firmware. This fork adds correct support.

**ME 14 (Comet Lake LP)** wrote to `fpsba+0x80` (PCHSTRP32). The correct location is `fpsba+0x70` (PCHSTRP28, bit 16). Confirmed via binary diff on real hardware — a single bit changes at `+0x70`, nothing changes at `+0x80`.

**ME 15 (Tiger Lake)** had no LP/H distinction. Tiger Lake LP uses PCHSTRP31 at `fpsba+0x7C`. Tiger Lake H and Rocket Lake H share the Tiger Point PCH-H, which uses PCHSTRP37 at `fpsba+0x94`. Both are now confirmed and auto-detected.

**ME 16/16.1 (Alder/Raptor Lake)** — several forks used `fpsba+0xDC` (PCHSTRP55). Wrong. The correct location is PCHSTRP31 bit 16. Writing to byte `0x017E` is identical to setting PCHSTRP31 bit 16 — they are the same bit expressed differently, not two different locations.

**ME 18 (Meteor Lake)** — this fork does not attempt to write. MTL dropped the discrete PCH. The descriptor layout changed entirely. No confirmed HAP offset exists. The tool prints a clear warning and exits cleanly without touching the image.

---

## HAP Bit Locations

| ME Version | Platform | HAP Location | Status |
|---|---|---|---|
| ME 12 LP | 8th/9th gen U-series | PCHSTRP28 — `fpsba+0x70` bit 16 | Confirmed |
| ME 12 H | 8th/9th gen H-series / desktop | PCHSTRP32 — `fpsba+0x80` bit 16 | Confirmed |
| ME 13 | Ice Lake LP | PCHSTRP28 — `fpsba+0x70` bit 16 | Confirmed |
| ME 14 | Comet Lake LP | PCHSTRP28 — `fpsba+0x70` bit 16 | Confirmed |
| ME 15 LP | Tiger Lake LP | PCHSTRP31 — `fpsba+0x7C` bit 16 | Confirmed |
| ME 15 H | Tiger Lake H / Rocket Lake H | PCHSTRP37 — `fpsba+0x94` bit 16 | Confirmed |
| ME 16 | Alder Lake | PCHSTRP31 — `fpsba+0x7C` bit 16 | Confirmed |
| ME 16.1 | Raptor Lake | PCHSTRP31 — `fpsba+0x7C` bit 16 | Confirmed |
| ME 18 | Meteor Lake | Unknown — write intentionally skipped | Unconfirmed |

The LP/H split for ME 12 and ME 15 is handled automatically. The tool reads both straps and selects the correct one based on which register is populated.

---

## Usage

```bash
# Back up first. Always.
sudo flashrom -p internal -r stock.bin

# Check current HAP state — read-only, nothing is written
python3 me_cleaner.py -c stock.bin

# Set the HAP bit — writes to a new output file, never modifies the input
python3 me_cleaner.py -s stock.bin -O patched.bin

# Verify the patch before flashing
python3 me_cleaner.py -c patched.bin

# Flash
sudo flashrom -p internal -w patched.bin
```

After reboot: ME absent from lspci, BIOS ME version field blank, all ME communication tools return nothing.

---

## Module Removal

Module removal (`-S` flag) is not supported on ME 12+ IFWI firmware. Attempting it corrupts the image. On IFWI firmware the tool automatically detects this, skips the removal step with a clear warning, and proceeds to set the HAP bit correctly.

On pre-8th gen hardware the `-S` flag works as normal.

---

## Meteor Lake

ME 18 (Meteor Lake) gets its own section because it deserves one. MTL uses a tile architecture with no discrete PCH. The flash descriptor layout is completely different from every previous generation — there are no PCH straps at `0x100`. Writing there on MTL does nothing, silently.

This fork will not write to an unconfirmed location and claim success. When the correct HAP offset for MTL is confirmed from a real firmware dump, it will be added. Until then the tool exits with a clear explanation.

If you have an MTL machine and can provide a before/after firmware dump with HAP set via Intel FIT, please open an issue.

---

## Companion Tools

This fork is part of a set of three tools covering the same platform range:

- **[ifdtool-thinkpad](https://github.com/MangoKiwiPlumGrape/ifdtool_thinkpad)** — fixes HAP bit read and write for CNL through RPL. Upstream ifdtool silently writes to the wrong strap on every platform from 8th gen onwards.
- **[intelmetool-thinkpad](https://github.com/MangoKiwiPlumGrape/intelmetool_thinkpad)** — fixes platform detection so ME status can actually be queried on 8th gen and newer. Upstream exits with "ME not present" on every post-7th gen machine.

---

## Credits

Original me_cleaner by Nicola Corna — Copyright (C) 2016–2018
License: GNU GPL v3 — https://github.com/corna/me_cleaner

ME 12 H (PCHSTRP32) findings: PR #282
ME 15/16 initial HAP offsets: XutaxKamay — https://github.com/XutaxKamay/me_cleaner

Hardware confirmation for ME 14 CML-LP, ME 15 LP/H strap split, and ME 16/16.1 datasheet cross-reference: this fork.

---

## License

GNU General Public License v3 — see [LICENSE](LICENSE) for full terms.
You must retain the original copyright notice when distributing modified versions.
