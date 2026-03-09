# me_cleaner — HAP Soft-Disable Fork (8th–14th Gen Intel)

> Fork of [corna/me_cleaner](https://github.com/corna/me_cleaner) focused on **correctly setting the HAP (High Assurance Platform) bit** on Intel platforms from 8th through 14th generation, with hardware-confirmed offsets for ThinkPad LP/U-series machines.

---

## What This Fork Fixes

The original me_cleaner v1.2 has two problems on modern ThinkPads:

**Problem 1 — ME 14 (10th gen, Comet Lake LP) writes to the wrong strap.**
The original hardcodes `fpsba+0x80` (PCHSTRP32) for ME 14. On Comet Lake LP boards (ThinkPad X13, X1C Gen 8, T14 etc.) the HAP bit lives in `fpsba+0x70` (PCHSTRP28) at bit 16. Writing to `+0x80` silently does nothing — the image passes RSA validation but ME is never disabled.

**Problem 2 — ME 13 (Ice Lake, 10th gen) is completely missing.**
The original has no version mapping for ME 13 at all. Ice Lake systems fall through with undefined behaviour.

---

## Hardware-Confirmed HAP Bit Locations

These offsets were verified by diffing stock BIOS dumps against Intel FIT-patched reference images, byte by byte:

| Platform | ME Version | ThinkPad | HAP Location | Confirmed |
|---|---|---|---|---|
| Coffee Lake U (8th gen) | ME 12.0.x | X1 Carbon Gen 6 | `fpsba+0x70` bit 16 | ✅ |
| Whiskey Lake U (8th gen) | ME 12.0.x | X1 Carbon Gen 7 | `fpsba+0x70` bit 16 | ✅ |
| Comet Lake U LP (10th gen) | ME 14.1.x | X13 Gen 1 | `fpsba+0x70` bit 16 | ✅ |
| Cannon Lake H (desktop) | ME 12.0.x | Z390/H370/B360 | `fpsba+0x80` bit 16 | ✅ via PR#282 |

**Proof for CML-U LP (X13 Gen 1):**
```
stock   PCHSTRP28 = 0x801801b8   (HAP bit 16 = 0)
patched PCHSTRP28 = 0x801901b8   (HAP bit 16 = 1)
diff    =           0x00010000   ← exactly one bit
cmp -l byte 371 = fpsba(0x100) + 0x70 + 3 (byte 3 of dword)
```

---

## Changes vs Original me_cleaner v1.2

| Change | Original | This Fork |
|---|---|---|
| ME 14 HAP offset | `fpsba+0x80` ❌ | `fpsba+0x70` ✅ confirmed |
| ME 13 (Ice Lake) | missing — crashes | mapped to gen 4, `fpsba+0x70` |
| ME 12 LP vs H | `fpsba+0x70` only | LP heuristic: `+0x70` or `+0x80` |
| IFWI warning | silent skip | explicit warning, continues to HAP |
| Version string | `1.2` | `1.2-thinkpad-fork` |

---

## Supported Platforms

This fork is focused on **soft-disable via HAP bit only** (`-s` / `-S` flags). Module removal (`-S` without `-s`) is **not supported** on ME 12+ IFWI firmware — attempting it corrupts the image. The script will warn you and skip it automatically.

| Generation | CPU | ME Version | HAP Path | Status |
|---|---|---|---|---|
| 8th gen (U) | Coffee Lake / Whiskey Lake | ME 12.0.x | gen 4 → `fpsba+0x70` | ✅ hardware confirmed |
| 9th gen (U) | Coffee Lake Refresh | ME 12.0.x | gen 4 → `fpsba+0x70` | ✅ hardware confirmed |
| 10th gen (U) | Comet Lake LP | ME 14.1.x | gen 5 → `fpsba+0x70` | ✅ hardware confirmed (X13 Gen1) |
| 8th/9th gen (H) | Cannon Lake H | ME 12.0.x | gen 4 → `fpsba+0x80` | ✅ hardware confirmed via PR#282 |
| 10th gen (U) | Ice Lake | ME 13.x.x | gen 4 → `fpsba+0x70` | ⚠️ unmapped in all forks — logic added, untested |
| 11th gen | Tiger Lake | ME 15.x.x | gen 6 → `fpsba+0x7C` | ⚠️ works on some boards, RSA INVALID reported on others |
| 12th gen+ | Alder Lake / Raptor Lake | ME 16.x.x | gen 7 → `fpsba+0xDC` | ⚠️ XutaxKamay stated "not sure about this one" — use with caution |

---

## Usage

```bash
# 1. Make a backup of your current BIOS first — always
sudo flashrom -p internal -r stock_backup.bin

# 2. Check current state (no writes, safe to run)
python3 me_cleaner.py -c stock_backup.bin

# 3. Patch HAP bit only into a new output file (recommended)
python3 me_cleaner.py -s -O patched.bin stock_backup.bin

# 4. Verify the patch looks correct before flashing
python3 me_cleaner.py -c patched.bin
# Should print: The HAP bit is SET

# 5. Flash patched image
sudo flashrom -p internal -w patched.bin
```

---

## Verifying It Worked After Reboot

```bash
# ME should disappear from PCI bus
lspci | grep -i "mei\|management engine\|heci"
# → should return nothing

# If you have intelmetool
sudo intelmetool -m
# → should show "Error 198: ME disabled" or ME version 0.0.0.0
```

---

## Requirements

- Python 3
- `flashrom` for dumping/flashing
- Root access
- A full BIOS dump (not just the ME region) — `-s` requires a full dump

---

## Important Warnings

- **Always back up your BIOS before flashing.** Use `flashrom -p internal -r backup.bin`.
- This is a **soft/firmware-level disable** only. The ME hardware still exists. It halts itself after hardware init when the HAP bit is set.
- This does **not** remove ME modules. On IFWI firmware (ME 12+) module removal is not possible without corrupting the image.
- Tested on ThinkPads. Other vendors may have different `fpsba` layouts — always run `-c` first and verify the output makes sense before using `-s`.
- If `-c` reports the HAP bit as already SET on your stock image, do not patch — it's already disabled.

---

## Credits

Original me_cleaner by **Nicola Corna** — Copyright (C) 2016-2018  
License: GNU GPL v3  
Source: https://github.com/corna/me_cleaner

ME 12 H (PCHSTRP32) findings: PR#282 by @ghost / @davidmartinzeus  
ME 15/16 HAP offsets: **XutaxKamay** — https://github.com/XutaxKamay/me_cleaner  
(note: ME 15/16 offsets are not fully confirmed across all boards — see platform table above)

**HAP offset hardware confirmation for ME 14 CML-LP (this fork):**  
Verified via byte-level diff of stock vs Intel FIT-patched BIOS on ThinkPad 10th gen comet lake  
`stock 0x801801b8 → patched 0x801901b8 — diff = 0x00010000 (bit 16 of PCHSTRP28)`

---

## What Happens After Setting HAP

Once the patched BIOS is flashed, the Intel ME halts itself immediately after hardware initialisation. No tool, driver or OS interface can communicate with it.

### BIOS / Firmware
- ME version field is **empty/blank**
- No ME information is displayed anywhere in the BIOS

### lspci
```bash
$ lspci | grep -i "mei\|management engine\|heci"
# returns nothing
```

### Intel MEInfo
```bash
$ sudo ./MEInfo
# returns nothing — no ME interface to talk to
```

### intelmetool
```bash
$ sudo intelmetool -m
# returns nothing — no ME interface to talk to
```

### MEAnalyzer
Cannot communicate with the live ME. Can still parse the BIOS **file** and will confirm `HAP/AltMeDisable: Yes`.

### Summary
| Tool | Before HAP | After HAP |
|---|---|---|
| BIOS ME version | 14.x.x.x | **blank** |
| `lspci` | visible | **nothing** |
| MEInfo | returns ME data | **nothing** |
| intelmetool | returns ME data | **nothing** |
| MEAnalyzer (file) | HAP = No | HAP = Yes |
| Any ME tool (live) | functional | **no device to bind to** |

## License

GNU General Public License v3 — see [LICENSE](LICENSE) for full terms.  
You must retain the original copyright notice when distributing modified versions.
