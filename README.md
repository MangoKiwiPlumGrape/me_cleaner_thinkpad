<div align="center">

# me_cleaner v1.3 — HAP Fork

### Confirmed Intel ME disable for 8th–15th gen Intel platforms

[![ME 12](https://img.shields.io/badge/ME%2012-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 13](https://img.shields.io/badge/ME%2013-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 14](https://img.shields.io/badge/ME%2014-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 15](https://img.shields.io/badge/ME%2015-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 16](https://img.shields.io/badge/ME%2016-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 18](https://img.shields.io/badge/ME%2018-unconfirmed-red?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](https://www.gnu.org/licenses/gpl-3.0)
[![Fork of](https://img.shields.io/badge/fork%20of-corna%2Fme__cleaner-lightgrey?style=flat-square)](https://github.com/corna/me_cleaner)
[![Hardware Tested](https://img.shields.io/badge/hardware-tested%20%26%20flashed-success?style=flat-square)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

> Fork of [corna/me_cleaner](https://github.com/corna/me_cleaner) with correct HAP bit offsets for 8th–14th gen Intel platforms. Every offset is confirmed. If you have been using another fork and ME is still running after a flash, this is probably why.

</div>

---

## The Problem With Other Forks

The original me_cleaner v1.2 and most forks silently write the HAP bit to the wrong location on several platforms. The tool reports success, the binary changes, and ME keeps running. You would never know it failed unless you checked with a separate tool afterwards.

**ME 13 (Ice Lake, 10th gen)** is completely absent from the original. Running it on an ICL image produces an error and exits.

**ME 14 (Comet Lake LP, 10th gen)** is mapped to the wrong strap. The original writes to `fpsba+0x80` (PCHSTRP32). The correct location is `fpsba+0x70` (PCHSTRP28 bit 16). Confirmed via binary diff on real hardware — one byte changes at `fpsba+0x70`, nothing changes at `fpsba+0x80`.

**ME 15 (Tiger Lake, 11th gen)** is split by PCH variant. LP boards use PCHSTRP31 at `fpsba+0x7C`. H-series boards (Tiger Lake H, Rocket Lake H) use PCHSTRP37 at `fpsba+0x94`. Most forks either skip ME 15 entirely or apply the LP offset to everything. This fork detects the correct strap automatically.

**ME 16/16.1 (Alder/Raptor Lake)** is wrong in several other forks which use `fpsba+0xDC` (PCHSTRP55). The HAP bit lives in PCHSTRP31 bit 16. Writing to byte `0x017E` in the descriptor is identical — it is byte 2 of the PCHSTRP31 dword at `fpsba+0x7C`. Same bit, different addressing.

**ME 18 (Meteor Lake)** is not written. MTL dropped the discrete PCH entirely. The descriptor layout changed and no confirmed HAP offset exists. This fork exits with a clear warning rather than writing to an unconfirmed location and calling it a success.

---

## HAP Bit Locations

| ME Version | Platform | HAP Location |
|---|---|---|
| ME 12 LP | Coffee / Whiskey / Cannon Lake U (8th/9th gen) | PCHSTRP28 — `fpsba+0x70` bit 16 |
| ME 12 H | Cannon Lake H, Z390/H370 desktop | PCHSTRP32 — `fpsba+0x80` bit 16 |
| ME 13 | Ice Lake LP (10th gen) | PCHSTRP28 — `fpsba+0x70` bit 16 |
| ME 14 | Comet Lake LP (10th gen) | PCHSTRP28 — `fpsba+0x70` bit 16 |
| ME 15 LP | Tiger Lake LP (11th gen) | PCHSTRP31 — `fpsba+0x7C` bit 16 |
| ME 15 H | Tiger Lake H / Rocket Lake H | PCHSTRP37 — `fpsba+0x94` bit 16 |
| ME 16 | Alder Lake (12th gen) | PCHSTRP31 — `fpsba+0x7C` bit 16 |
| ME 16.1 | Raptor Lake (13th gen) | PCHSTRP31 — `fpsba+0x7C` bit 16 |
| ME 18 | Meteor Lake (14th gen) | Unknown — write skipped |

The LP vs H split for ME 12 and ME 15 is handled automatically. The tool reads both candidate straps and selects the correct one based on which register is populated on the target platform.

---

## Usage

Internal flashing is blocked on every modern ThinkPad and most other platforms from 8th gen onwards. You need an external SPI programmer — a CH341A with a SOIC8 clip is the standard setup.

**1. Find your chip**

Run flashrom with your programmer to identify the chip and confirm the clip is seated:

```
sudo flashrom -p ch341a_spi
```

It will print the detected chip name, e.g. `MX25L12835F`. If it errors or returns garbage, reseat the clip.

**2. Read the chip — do this twice and verify they match**

```
sudo flashrom -p ch341a_spi -c MX25L12835F -r stock_1.bin
sudo flashrom -p ch341a_spi -c MX25L12835F -r stock_2.bin
md5sum stock_1.bin stock_2.bin
```

Both hashes must be identical before you proceed. If they differ, the clip connection is unreliable — fix it first.

**3. Check current HAP state**

```
python3 me_cleaner.py -c stock_1.bin
```

If it already says `The HAP bit is SET`, ME is already disabled. Stop here.

**4. Patch**

```
python3 me_cleaner.py -s stock_1.bin -O patched.bin
```

**5. Verify the patch**

```
python3 me_cleaner.py -c patched.bin
```

Should print `The HAP bit is SET`.

**6. Write**

```
sudo flashrom -p ch341a_spi -c MX25L12835F -w patched.bin
```

**7. Verify the write**

```
sudo flashrom -p ch341a_spi -c MX25L12835F -v patched.bin
```

After reboot: ME disappears from lspci, the BIOS ME version field goes blank, and any ME communication tool returns nothing. That is a successful disable.

---

## Module Removal

Module removal (`-S` flag) is not supported on ME 12+ IFWI firmware. The partition structure changed with 8th gen and stripping modules corrupts the image. The tool detects IFWI firmware automatically, skips the removal step with a clear warning, and still sets the HAP bit correctly.

If you are on pre-8th gen hardware the `-S` flag works as it always has.

---

## Meteor Lake

ME 18 will not be written until the HAP offset is confirmed. MTL uses a tile architecture with no discrete PCH — there are no PCH straps at `fpsba+0x100`. Writing there does nothing. The tool exits with an explanation rather than silently patching the wrong location. If you have an MTL machine and can provide a before/after firmware dump, open an issue.

---

## Companion Tools

- **[ifdtool-thinkpad](https://github.com/MangoKiwiPlumGrape/ifdtool_thinkpad)** — upstream ifdtool reads and writes the wrong strap on CNL/ICL/CML/TGL/RKL. Fixed for the same platform range as this fork.
- **[intelmetool-thinkpad](https://github.com/MangoKiwiPlumGrape/intelmetool_thinkpad)** — upstream exits with "ME not present" on every post-7th gen machine due to missing device IDs. Fixed for 8th gen through Panther Lake.

---

## Credits

Original me_cleaner by Nicola Corna — Copyright (C) 2016–2018. License: GNU GPL v3.

ME 12 H-series offset: PR#282.
ME 15/16 initial work: XutaxKamay.
ME 13/14 corrections, ME 15 H-series, and ME 16/16.1 confirmation: this fork.
