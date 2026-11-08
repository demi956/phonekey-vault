# PhoneKey Vault: phone-keyed, low-bandwidth PC recovery for students

**White paper · v0.1 · November 2026 · demi956**

## Abstract

PhoneKey Vault is an encrypted backup and recovery system in which a smartphone holds the master key to a PC's backups:

- **Backups need no phone.** The PC backs up continuously with its own device key.
- **Restores need the phone.** Any restore onto a new machine needs the phone's approval, or an offline recovery phrase.
- **Storage is untrusted.** Cloud storage only ever holds data encrypted on the PC.

The system targets university students in bandwidth-constrained markets, starting with Ghana. It restores in three tiers:

1. Essentials, from the phone over USB.
2. Active projects, from the cloud.
3. Everything else, in the background on Wi-Fi.

A working prototype (Python + restic) shows the full key lifecycle: pairing, backup, phone-approved restore, revocation and recovery.

## 1. Problem

Students lose work to four common events: theft, hardware failure, ransomware and accidental deletion. Backup habits are weak everywhere:

- 84% of US computer owners say they've backed up all their data, yet only 15% feel certain their files are safe.
- 74% report accidentally deleting important data.

Both figures are from [Backblaze, 2024](https://backblaze.com/blog/2024-state-of-the-backup-security-incidents-and-data-loss-on-the-rise/). An older student survey found 46% had lost data in a crash, and 68% backed up less than monthly ([BYU / Mozy, 2009](https://universe.byu.edu/2009/03/13/data-loss-an-easily-preventable-problem/)).

Two constraints make the problem harder in Ghana:

- **Cost:** mobile data costs $0.40–$0.96 per GB ([Citi Newsroom, Feb 2025](https://citinewsroom.com/2025/02/data-cost-in-ghana-remains-high-despite-low-cost-ranking/)).
- **Speed:** average fixed broadband is 55.9 Mbps down and 28.3 Mbps up, and mobile is 35.1 down and 16 up ([Ookla Global Index via Worlddata, Aug 2026](https://www.worlddata.info/africa/ghana/telecommunication.php)).

At those numbers, a 200 GB restore takes about 8 hours on average fixed broadband, or about 89 hours on a 5 Mbps shared hostel connection. Over mobile data it would cost $80–$192.

## 2. Existing solutions and their gaps

| Product | Price (Nov 2026) | Gap for this audience |
| --- | --- | --- |
| Windows Backup | Free, 5 GB of OneDrive | Small quota; restores only during new-PC setup; desktop apps must be reinstalled by hand |
| Backblaze Personal | $99/year | Files only; costly for students |
| IDrive Personal | $6.99/month billed yearly, first year, 5 TB | Far more storage than students need; price rises after year one |
| Acronis True Image | $49.99–$124.99/year | Strong disk imaging, but complex; cloud starts at the $57.99 tier |
| Google Drive / OneDrive sync | 15 GB / 5 GB free | Sync isn't backup: deletions and encrypted files sync too; no app restore |

None of these combines a student price, a phone-as-key model and a restore designed for scarce bandwidth.

## 3. Design

### 3.1 Components

- **PC agent.** Watches chosen folders, encrypts locally, uploads only what changed, records installed apps and settings, and skips junk (caches, `node_modules`, installers).
- **Vault.** Any S3-compatible or user-owned storage. It holds encrypted, deduplicated chunks and has no access to any key.
- **Phone.** Holds the master key in secure hardware. It approves restores, revokes devices, and keeps an encrypted "essentials" copy for offline restore.

### 3.2 Key hierarchy

| Key | Where it lives | Can do | Revocable |
| --- | --- | --- | --- |
| Master key | Phone; recovery phrase on paper | Everything, including adding and removing device keys | Rotate via recovery |
| Device key (one per PC) | That PC only, protected by OS key storage (Windows DPAPI) | Back up and restore on that PC | Yes, from the phone |
| One-time pad (per request) | Inside the QR code shown for that request only | Masks the master key in transit, once | Expires after use |

The prototype uses restic's multiple-key support, where any of several passwords unlocks the same repository. Each paired PC adds its own key; theft mode removes it.

### 3.3 Flows

1. **Pairing.** The PC creates the vault with a random master key and adds its own device key. It shows the master key to the phone inside a QR code's URL fragment, which browsers never send over the network, then discards it. A recovery phrase is shown once.
2. **Backup.** Uses only the device key, so it works without the phone.
3. **Restore on a new PC.** The new PC generates a request ID and a 64-byte one-time pad, and shows both in a QR code. The phone shows what is being requested and by which machine. On approval, the phone returns the master key XOR the pad. The new PC unmasks it, opens the vault, restores, and enrols its own device key.
4. **Theft mode.** With phone approval, the master key removes the stolen PC's device key, and the vault rejects that PC from then on.
5. **Recovery.** The recovery phrase stands in for the phone in any flow.

### 3.4 Three-tier restore

| Tier | What | Channel | Example time |
| --- | --- | --- | --- |
| 1 | Essentials chosen by the user (5–20 GB) | Phone over USB | ~6 minutes for 10 GB at 30 MB/s; no data cost |
| 2 | Active projects | Cloud, priority order | Minutes to hours |
| 3 | Everything else | Cloud, Wi-Fi only, background | Overnight |

## 4. Threat model

| Threat | Mitigation |
| --- | --- |
| Laptop stolen | Device key is revoked from the phone; the vault is encrypted; the master key was never on the laptop |
| Laptop and phone stolen together | Thief lacks the phone unlock (biometric in the native app) and the paper recovery phrase |
| Storage provider breached | Only encrypted chunks are stored; names are encrypted too |
| Ransomware on the PC | Version history; production design makes old versions append-only from the PC's side |
| Malicious device on the same Wi-Fi | Prototype: the key travels masked by a one-time pad that only crossed via QR. Production: an authenticated, encrypted channel (TLS with key pinning, or a Noise handshake seeded from the QR code) |
| User loses phone and recovery phrase | Optional 2-of-3 trusted-contact recovery (Shamir secret sharing); otherwise unrecoverable by design, and stated at sign-up |

## 5. Prototype

- **Code:** `phonekey.py` (about 380 lines, Python standard library only) with `restic` 0.19 as the encryption engine. The PC page shows the QR code; the phone page holds the key and approves.
- **Verified by `test_e2e.py`:**
  - pairing;
  - backup;
  - a denied restore that changes nothing;
  - an approved restore with a byte-for-byte match;
  - junk exclusion;
  - backup from the new PC;
  - revocation locking out the old PC;
  - rejection of a wrong key.
- **Manual check:** a real restore approved through the phone page in a mobile browser.

## 6. Economics

| Plan | Price | Storage | Storage cost/month |
| --- | --- | --- | --- |
| Free | $0 | User's own Google Drive / OneDrive | $0 |
| Student | $1.50/month | 100 GB | $0.70 ([B2 at $6.95/TB](https://www.backblaze.com/cloud-storage/pricing)) |
| Campus licence | ~$5 per student per year | 50 GB | ~$0.35 |

Assuming about $200 a month in fixed costs, break-even is about 267 paying Student-plan users.

## 7. Roadmap and future work

- **Next:**
  - a Flutter phone app with Keystore / Secure Enclave and biometric unlock;
  - a scheduled background agent;
  - app reinstall through winget;
  - settings capture;
  - a phone essentials copy;
  - mobile-money payments.
- **CampusMesh.** Students lend spare disk space and back each other up across the campus network using erasure coding. A 10-of-30 split survives with 99.9% availability even if each laptop is online only 60% of the time, and restores 10 GB in about 80 seconds over a 1 Gbps campus network.
- **Ghost Desk.** Scan a lab PC's QR code to open your workspace on it, then wipe it when you leave.

## 8. Conclusion

Backup is a crowded market, but recovery isn't solved for students on scarce bandwidth. Making the phone the key, and planning the restore around the network people actually have, gives PhoneKey Vault a clear, testable position. The prototype shows the key lifecycle works. The next milestone is a 30-student pilot on one campus.

## References

1. [Backblaze, 2024 State of the Backup](https://backblaze.com/blog/2024-state-of-the-backup-security-incidents-and-data-loss-on-the-rise/)
2. [BYU Daily Universe, student data-loss survey (2009)](https://universe.byu.edu/2009/03/13/data-loss-an-easily-preventable-problem/)
3. [Citi Newsroom, cost of 1 GB of data in Ghana (Feb 2025)](https://citinewsroom.com/2025/02/data-cost-in-ghana-remains-high-despite-low-cost-ranking/)
4. [Worlddata.info, Ghana telecommunication (Ookla Global Index, Aug 2026)](https://www.worlddata.info/africa/ghana/telecommunication.php)
5. [Microsoft, Windows Backup](https://support.microsoft.com/help/5029731)
6. Pricing pages, checked 7 Nov 2026: [Backblaze Personal](https://www.backblaze.com/cloud-backup/pricing), [Backblaze B2](https://www.backblaze.com/cloud-storage/pricing), [IDrive](https://www.idrive.com/pricing), [Acronis](https://www.acronis.com/en/products/true-image/purchasing/), [Google One](https://one.google.com/about/plans)
7. [restic](https://restic.net)
