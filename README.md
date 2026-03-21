<div align="center">

# me_cleaner v1.3 — HAP Fork

### Confirmed Intel ME disable for 8th–16th gen Intel platforms

[![ME 12](https://img.shields.io/badge/ME%2012-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 13](https://img.shields.io/badge/ME%2013-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 14](https://img.shields.io/badge/ME%2014-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 15](https://img.shields.io/badge/ME%2015-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 16](https://img.shields.io/badge/ME%2016-confirmed-brightgreen?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)
[![ME 18](https://img.shields.io/badge/ME%2018-unconfirmed-red?style=flat-square&logo=intel)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue?style=flat-square)](https://www.gnu.org/licenses/gpl-3.0)
[![Fork of](https://img.shields.io/badge/fork%20of-corna%2Fme__cleaner-lightgrey?style=flat-square)](https://github.com/corna/me_cleaner)
[![Hardware Tested](https://img.shields.io/badge/hardware-tested%20%26%20flashed-success?style=flat-square)](https://github.com/MangoKiwiPlumGrape/me_cleaner_thinkpad)

> Fork of [corna/me_cleaner](https://github.com/corna/me_cleaner) with correct HAP bit offsets for 8th–16th gen Intel platforms. Every offset is confirmed. If you have been using another fork and ME is still running after a flash, this is probably why.

</div>

---

## The Problem With Other Forks

The original me_cleaner v1.2 and most forks silently write the HAP bit to the wrong location on several platforms. The tool reports success, the binary changes, and ME keeps running. You would never know it failed unless you checked with a separate tool afterwards.

**ME 13 (Ice Lake, 10th gen)** is completely absent from the original. Running it on an ICL image produces an error and exits.

**ME 14 (Comet Lake LP, 10th gen)** is mapped to the wrong strap. The original writes to `fpsba+0x80` (PCHSTRP32). The correct location is `fpsba+0x70` (PCHSTRP28 bit 16). Confirmed via binary diff on real hardware — one byte changes at `fpsba+0x70`, nothing changes at `fpsba+0x80`.

**ME 15 (Tiger Lake, 11th gen)** is split by PCH variant. LP boards use PCHSTRP31 at `fpsba+0x7C`. H-series boards (Tiger Lake H, Rocket Lake H) use PCHSTRP37 at `fpsba+0x94`. Most forks either skip ME 15 entirely or apply the LP offset to everything. This fork detects the correct strap automatically.

**ME 16/16.1 (Alder/Raptor Lake)** is split by PCH variant. PCH-P/N mobile platforms (ThinkPads, laptops) use PCHSTRP31 at `fpsba+0x7C` — byte `0x017E`. PCH-S desktop platforms (Z690/H670/B660) use PCHSTRP55 at `fpsba+0xDC` — byte `0x01DE`. The fork detects the correct variant automatically using the `fpsba+0xD0`.

**ME 18 (Meteor Lake)** is not written. MTL dropped the discrete PCH entirely. The descriptor layout changed and no confirmed HAP offset exists. This fork exits with a clear warning rather than writing to an unconfirmed location and calling it a success.

---

## HAP Bit Locations

| ME Version | Platform | HAP Location |
|---|---|---|
| ME 12 LP | Coffee / Whiskey / Cannon Lake U (8th/9th gen) | PCHSTRP28 — `fpsba+0x70` bit 16 |
| ME 12 H | Cannon Lake H, Z390/H370 desktop | PCHSTRP32 — `fpsba+0x80` bit 16 |
| ME 13 | Ice Lake LP (10th gen) | PCHSTRP28 — `fpsba+0x70` bit 16 |
| ME 13 | Jasper Lake (Atom N-series) | PCHSTRP26 — `fpsba+0x68` bit 16 |
| ME 14 LP | Comet Lake LP (10th gen) | PCHSTRP28 — `fpsba+0x70` bit 16 |
| ME 14 S | Comet Lake S desktop | PCHSTRP32 — `fpsba+0x80` bit 16 |
| ME 15 LP | Tiger Lake LP (11th gen) | PCHSTRP31 — `fpsba+0x7C` bit 16 |
| ME 15 H | Tiger Lake H / Rocket Lake H | PCHSTRP37 — `fpsba+0x94` bit 16 |
| ME 15 | Elkhart Lake (Atom x6000) | PCHSTRP33 — `fpsba+0x84` bit 16 |
| ME 16 PCH-P/N | Alder Lake mobile (12th gen) | PCHSTRP31 — `fpsba+0x7C` bit 16 |
| ME 16 PCH-S | Alder Lake S desktop | PCHSTRP55 — `fpsba+0xDC` bit 16 |
| ME 16.1 PCH-P/N | Raptor Lake mobile (13th gen) | PCHSTRP31 — `fpsba+0x7C` bit 16 |
| ME 16.1 PCH-S | Raptor Lake S desktop | PCHSTRP55 — `fpsba+0xDC` bit 16 |
| ME 18 | Meteor Lake (14th gen) | Unknown — write skipped on stable branch |

The LP vs H and PCH-S vs PCH-P/N splits are handled automatically. The tool reads the relevant discriminator straps and selects the correct HAP location for the target platform.

---

## Dual-Chip ThinkPads — ME 16 vPro Warning

**If you have a ThinkPad T14 Gen3/Gen4 or similar 12th/13th gen Corporate vPro model, read this before proceeding.**

Newer ThinkPad Corporate/vPro SKUs (12th gen and later) use a dual-chip SPI flash configuration with Lenovo ThinkShield firmware protection:

- **Main chip (Winbond)** — boots the system, contains the full BIOS and ME region
- **Backup chip (GigaDevice)** — EC-managed recovery chip, contains a copy of the Flash Descriptor

On these machines the Flash Descriptor carries a cryptographic signature verified by the Embedded Controller. When the main chip is modified, the EC detects a mismatch on the next boot, triggers a double-reboot recovery sequence, and restores the original image from the GigaDevice. The HAP patch gets wiped before the OS even loads.

This is a ThinkShield feature specific to **12th gen and later Corporate/vPro SKUs**. It does not affect Consumer ThinkPad SKUs of the same generation. It also does not affect older vPro ThinkPads — 8th gen and 11th gen vPro machines with dual chips patch successfully with this tool.

**There is currently no known way to set the HAP bit permanently on these machines.** The Flash Descriptor is cryptographically signed with a Lenovo key. Patching the GigaDevice backup chip triggers an EC integrity check that also causes a boot failure.

To check whether your ThinkPad is affected:

```
./ifdtool -d -p adl your_dump.bin
```

Look for `CORP` and `SIGNED` in the OEM section output. If both are present you are on a ThinkShield-protected Corporate SKU and the HAP patch will not stick.

For these machines, use the OS-level fallback described below.

---

## Usage

Internal flashing is blocked on every modern ThinkPad and most other platforms from 8th gen onwards. You need an external SPI programmer — a CH341A with a SOIC8 clip is the standard setup.

**Note on WSON8 packages:** ThinkPad T14 Gen3/Gen4 and similar 12th gen+ models use WSON8 packages (small square chips, no legs) rather than SOIC8. A standard clip will not fit. You need a WSON8 pogo pin adapter for your programmer.

**1. Find your chip**

```
sudo flashrom -p ch341a_spi
```

**2. Read the chip twice and verify both reads match**

```
sudo flashrom -p ch341a_spi -c "CHIP" -r stock_1.bin
sudo flashrom -p ch341a_spi -c "CHIP" -r stock_2.bin
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
sudo flashrom -p ch341a_spi -c "CHIP" -w patched.bin
```

**7. Verify the write**

```
sudo flashrom -p ch341a_spi -c "CHIP" -v patched.bin
```

After reboot: ME disappears from lspci, the BIOS ME version field goes blank, and any ME communication tool returns nothing.

---

## Module Removal

Module removal (`-S` flag) is not supported on ME 12+ IFWI firmware. The partition structure changed with 8th gen and stripping modules corrupts the image. The tool detects IFWI firmware automatically, skips the removal step with a clear warning, and still sets the HAP bit correctly.

If you are on pre-8th gen hardware the `-S` flag works as it always has.

---

## Meteor Lake

ME 18 will not be written until the HAP offset is confirmed. MTL uses a tile architecture with no discrete PCH — there are no PCH straps at `fpsba+0x100`. Writing there does nothing. The tool exits with an explanation rather than silently patching the wrong location. If you have an MTL machine and can provide a before/after firmware dump produced by Intel FIT with `Reserved = Yes`, open an issue.

Experimental ME 18 support with a candidate offset (`0x21E`,  `me_spec_18.h`) is available in the `experimental/` folder. Use at your own risk and report back if it works.

---

## Fallback: OS-Level and Runtime Disable

If HAP patching is not possible on your machine — due to dual-chip ThinkShield protection, a locked flash descriptor, or any other reason — two fallback options are available.

### Runtime Soft-Disable — [mei_disable](https://github.com/MangoKiwiPlumGrape/mei_disable)

Sends the same `MKHI FWCAPS_SET_RULE` command used by coreboot, Dasharo, and System76 firmware to runtime-disable ME via the HECI interface. Works on ME 8 through CSME 18 without any firmware flashing — just root access and `/dev/mei0`.

```
# Build
make

# Disable ME for this session
sudo ./mei_disable

# Or use the Python version (no compilation needed)
sudo python3 mei_disable.py
```

**Important:** this is a runtime-only disable. ME re-enables itself on the next cold power cycle. Run it before `intel-me-disable.sh` to get soft-disable coverage for the current session. Corporate/vPro SKUs with ThinkShield may reject the command — the tool will tell you clearly if it does.

Also requires `/dev/mei0` to be present. If you have already run `intel-me-disable.sh`, the MEI driver is gone and this tool cannot send commands — run it first.

### Persistent OS-Level Disable — [intel-me-disable](https://github.com/MangoKiwiPlumGrape/intel-me-disable)

Removes all Intel MEI kernel drivers, installs udev rules to remove the ME PCI device on hotplug, and blacklists every ME-related kernel module. ME continues running in the PCH but has no interface to the OS — no `/dev/mei0`, no driver, invisible to userspace.

Covers Sandy Bridge (2011) through Panther Lake (2026). Works on Debian, Ubuntu, Arch, Fedora, Void, and any Linux distribution with udev.



---

## Companion Tools

**[ifdtool_thinkpad](https://github.com/MangoKiwiPlumGrape/ifdtool_thinkpad)** reads and dumps the flash descriptor correctly on modern platforms. Use the `-d` flag with your platform:

```
./ifdtool -d -p cml dump.bin    # Comet Lake
./ifdtool -d -p tgl dump.bin    # Tiger Lake LP
./ifdtool -d -p rkl dump.bin    # Tiger Lake H / Rocket Lake H
./ifdtool -d -p adl dump.bin    # Alder Lake
./ifdtool -d -p rpl dump.bin    # Raptor Lake
```

**[intelmetool_thinkpad](https://github.com/MangoKiwiPlumGrape/intelmetool_thinkpad)** queries live ME status after boot:

```
sudo ./intelmetool -m
```

With HAP set correctly it will show `Current Operation Mode: Soft Temporary Disable`.

**Note:** run intelmetool *before* intel-me-disable.sh — once the MEI driver is blacklisted there is nothing for intelmetool to talk to.

---

## Disclaimer

This tool modifies firmware. A bad flash can brick your machine. Read the chip twice, verify the md5, verify after writing, and keep your stock backup somewhere safe before you do anything.

This is firmware research provided as-is. I am not responsible for bricked hardware, data loss, or any other outcome.

---

## Credits

Original me_cleaner by Nicola Corna — Copyright (C) 2016–2018. License: GNU GPL v3.

ME 12 H-series offset: PR#282.
ME 15/16 initial work: XutaxKamay.
ME 13/14 corrections, ME 15 H-series, ME 16/16.1 confirmation, JSL/CML-S/EHL support, dual-chip GigaDevice support, ADL-S/RPL-S PCH-S discriminator: this fork.
HAP offsets cross-referenced against Dasharo coreboot `me_spec_*.h` and coreboot gerrit 88310.
