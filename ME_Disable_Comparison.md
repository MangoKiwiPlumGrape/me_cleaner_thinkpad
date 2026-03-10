# Intel ME Disable: HAP vs Soft-Disable

### A practical comparison of effectiveness across hardware generations

---

## 1. Background

Intel's Management Engine (ME) is a separate processor embedded in Intel chipsets that runs independently of the main CPU, persisting across power states and operating below the OS. Two primary mechanisms exist to disable or neuter it: the HAP (High Assurance Platform) bit approach and the older soft-disable method used by me_cleaner's `-S` flag.

This write-up documents a direct, hardware-observed comparison of both methods across two generations of Intel hardware — older 2011–2013 era Intel Macs (ME 8, Panther Point PCH) and 8th–10th gen Intel ThinkPads (ME 12–14, Cannon Point / Comet Lake PCH).

---

## 2. The Two Disable Methods

### 2.1 Soft-Disable (`me_cleaner -S`)

The soft-disable approach, implemented in me_cleaner via the `-S` flag, does two things simultaneously:

- Sets the HAP/AltMeDisable bit in the Flash Descriptor (PCHSTRP) — instructing ME to halt itself during bring-up
- Strips all ME firmware modules from the flash image except **FTPR** and **ROMP** — leaving the absolute minimum needed for a controlled, predictable halt

**FTPR** (Flash Primary) contains the bring-up code that reads the HAP strap and executes the halt. It cannot be removed — without it there is no controlled shutdown of ME and behaviour becomes undefined. **ROMP** is the ROM bypass module required for initial boot handoff before FTPR takes over.

The result is a belt-and-braces approach: even if HAP were somehow not read correctly, there are no remaining modules with meaningful capability to execute.

### 2.2 HAP Bit Only (`ifdtool` / `me_cleaner` without `-S`)

The HAP (High Assurance Platform) bit, also called AltMeDisable, is a single bit in the Flash Descriptor's PCHSTRP region. When set, ME reads it during bring-up and halts before loading any operational modules. This is a hardware-level mechanism — Intel built it in for government/classified deployments where ME must be provably inactive.

On newer platforms (8th gen onwards, ME 12+), setting HAP alone — without stripping any firmware modules — produces a fundamentally different hardware-level result compared to older platforms.

---

## 3. Observed Behaviour — Hardware Comparison

### 3.1 Older Platform: 2011–2013 Intel Mac (ME 8, Panther Point PCH)

**Method applied:** `me_cleaner -S` (HAP set + all modules stripped except FTPR/ROMP)

`intelmetool` output after patching:

```
ME PCI device is hidden
RCBA addr: 0xfed1c000
MEI was hidden on PCI, now unlocked
MEI found: [8086:1e3a] 7 Series/C216 Chipset Family MEI Controller #1
ME: Current Working State   : Initializing
ME: Current Operation Mode  : Debug
ME: Firmware Init Complete  : NO
ME: Manufacturing Mode      : YES
ME: Progress Phase State    : Check to see if straps say ME DISABLED
ME: failed to become ready
ME: GET FW VERSION message failed
```

**Key observations:**

- ME PCI device is hidden via the **FD2 register** (offset `0x3428`, bits 1–2) — MEI1D/MEI2D disable bits are set
- `intelmetool` was able to **unhide** the MEI device by writing to the RCBA/FD2 register directly
- After unhiding, full two-way MEI communication was established — intelmetool successfully read ME status registers
- ME is stuck in BUP phase, Manufacturing Mode, checking the HAP strap — never completes init
- The ME communication channel (MEI) is **technically still accessible** to root-level software

### 3.2 Newer Platform: 8th–10th Gen Intel ThinkPads (ME 12–14, CNL/CML PCH)

**Method applied:** HAP bit set only via `ifdtool` / `me_cleaner` (no module stripping)

**Observed state after patching:**

- BIOS ME version field: **blank**
- `lspci | grep -i mei` → **no output** — MEI device does not appear on PCI bus at all
- `intelmetool` → cannot find any MEI device to communicate with, exits immediately
- MEAnalyzer: `HAP/AltMeDisable: Yes`

`intelmetool` is completely unable to interrogate ME on these machines — not because the MEI device is hidden, but because it **does not enumerate on PCI at all**. There is no FD2 trick to unhide it. The communication channel is absent at the hardware level.

---

## 4. Side-by-Side Comparison

| Metric | Old Platform (2011–2013 Mac, ME 8) | New Platform (8th–10th Gen ThinkPad, ME 12–14) |
|--------|-----------------------------------|------------------------------------------------|
| Method applied | HAP + strip (`-S`) | HAP bit only |
| MEI on `lspci` | Hidden (present) | Absent entirely |
| MEI unhideable? | Yes — via FD2/RCBA | No — not enumerated |
| `intelmetool` result | Reads ME status | Cannot find device |
| ME completes init? | No | No |
| Communication channel | Accessible (root) | Not present |
| Modules remaining | FTPR + ROMP only | All (untouched) |

---

## 5. Analysis

The results reveal a counterintuitive finding: **HAP alone on newer platforms appears more effective at eliminating the ME communication channel** than the combined HAP+strip approach on older platforms.

### Why the difference?

On older platforms (ME 8, Panther Point), the MEI PCI device is disabled via the FD2 register — a software-accessible register in the RCBA memory-mapped region. This is a PCH-level feature disable, not a hardware absence. Any sufficiently privileged software can write to FD2 and re-enable the device, as `intelmetool` demonstrates.

On newer platforms (ME 12+, Cannon Point / Comet Lake), when HAP is set ME appears to halt **before the point at which the MEI PCI device is even enumerated**. The device never appears on the PCI bus — there is nothing to unhide because it was never presented to the bus fabric in the first place. This is a fundamentally earlier and lower-level shutdown.

### Does this mean module stripping is pointless on new platforms?

Not entirely. The HAP bit alone achieves a cleaner hardware result on new platforms, but me_cleaner's module stripping adds a meaningful second layer: if HAP were somehow bypassed or not read correctly, there would be no operational firmware left to run. It is defence in depth. The two approaches are complementary, not mutually exclusive.

However, on 8th gen+ hardware the practical result of HAP alone appears to exceed what the combined approach achieves on older hardware — at least in terms of eliminating the accessible MEI communication channel.

### The FD2 Register Concern

The fact that `intelmetool` can unhide the MEI device on older hardware by writing to FD2 is worth noting. This is not a theoretical attack — it is demonstrated by a tool that ships with coreboot and runs as root. On older platforms, "ME is disabled" is more accurately described as "ME is halted and its PCI device is soft-hidden." **The channel remains recoverable by privileged software.**

On newer platforms with HAP set, no such recovery appears possible from within the running OS. The device simply does not exist from the perspective of the PCI bus.

---

## 6. Conclusions

- HAP on 8th gen+ Intel hardware (ME 12+) eliminates the MEI PCI device at a lower level than the FD2 soft-hide used on older platforms
- Older soft-disable (HAP + strip) leaves the MEI communication channel technically accessible via FD2/RCBA writes from root
- `intelmetool` can be used as a practical test — if it can find and read the MEI device, the channel is still accessible; if it finds nothing, the disable is more complete
- Module stripping remains valuable as a second layer of defence regardless of platform generation
- The correct HAP strap offset is critical — writing to the wrong PCHSTRP (as upstream `ifdtool` does on CNL/ICL/CML) results in **silent failure** with no indication anything went wrong

---

## 7. Related Tools

The following patched utilities were used in this research, all with hardware-confirmed HAP bit fixes for 8th–10th gen platforms:

- **[me_cleaner-thinkpad](https://github.com/your-username/me_cleaner-thinkpad)** — fixes HAP offset for ME 13 (ICL, missing entirely) and ME 14 (CML, wrong offset `fpsba+0x80` → `fpsba+0x70`)
- **[ifdtool-thinkpad](https://github.com/your-username/ifdtool-thinkpad)** — fixes silent wrong-strap write on CNL/ICL/CML (upstream writes `pchstrp[0]` instead of `pchstrp[28]`)
- **[intelmetool-thinkpad](https://github.com/your-username/intelmetool-thinkpad)** — adds missing CNL/ICL/CML platform and MEI device IDs so intelmetool can actually detect these platforms

> All three upstream coreboot utilities stopped being updated for new platforms after approximately 2017, leaving 8th gen onwards silently broken.
