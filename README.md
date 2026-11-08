# PhoneKey Vault

**Your phone is your PC's key. If you lose the laptop, you keep your work.**

PhoneKey Vault is an open-source prototype of an encrypted PC backup that's unlocked and controlled from your phone:

- **Encrypted backups.** Your PC backs up into an encrypted vault.
- **The phone holds the master key.** It never stays on the PC.
- **Phone approval for restores.** A restore onto a new PC only happens after you approve it on your phone. If the phone is gone too, a recovery phrase works instead.

It's built for university students: people who carry their whole academic life on one laptop, rarely back it up, and often pay for every gigabyte of mobile data.

> **Status: working prototype (v0.1, November 2026).** The core flow works and is tested end to end. Don't use it as your only backup yet. See [Known limits](#known-limits).

## Why

- 84% of computer owners say they've backed up all their data, but only 15% feel certain their important files are safe ([Backblaze, 2024](https://backblaze.com/blog/2024-state-of-the-backup-security-incidents-and-data-loss-on-the-rise/)).
- Existing tools restore files, but not your working setup. Many of them assume fast, cheap, unlimited internet.

In Ghana, where this project started, mobile data costs $0.40–$0.96 per GB. At that price, restoring a 200 GB laptop over mobile data would cost $80–$192.

PhoneKey Vault's answer:

- The phone is the key.
- The cloud only ever holds encrypted data.
- Restores are planned around slow, expensive internet.

The full reasoning is in the [white paper](docs/WHITEPAPER.md).

## How it works

```
 Old PC ── encrypted backup ──▶ Vault (folder, Backblaze B2, Google Drive…)
   │                                   │
   └── QR pairing ──▶ Phone (master key)│
                         │             ▼
                         └─ approve ─▶ New PC ── restores your files
```

| What | How |
| --- | --- |
| Encryption | [restic](https://restic.net) (AES-256, deduplicated, versioned) |
| Phone holds the key | The master key reaches the phone inside a QR code and is never written to the PC's disk |
| Everyday backups | Each PC has its own device key, protected by Windows DPAPI |
| Restore approval | The new PC shows a QR code. The phone taps Approve and returns the key, masked with a one-time pad that only travelled inside that QR code. |
| Theft mode | `revoke` removes a stolen PC's key, so it can never open the vault again |
| Recovery | A recovery phrase is shown once at setup |

## Quick start (Windows, about 5 minutes)

You need **Python 3.10+** and **restic**:

```bash
winget install restic.restic
```

Your phone and PC must be on the **same Wi-Fi**.

**1. Create a vault and pair your phone.** Scan the QR code with your phone camera, and write down the recovery phrase.

```bash
python phonekey.py init --vault "%USERPROFILE%\PhoneKeyVault"
```

**2. Back up a folder.**

```bash
python phonekey.py backup "%USERPROFILE%\Documents\MyProject"
```

**3. Restore it, as if on a new PC.** Approve on your phone.

```bash
python phonekey.py restore --to "%USERPROFILE%\Desktop\Restored"
```

**Other commands:**

| Command | What it does |
| --- | --- |
| `snapshots` | List your backups |
| `keys` | List the vault's keys |
| `revoke KEY_ID` | Remove a lost PC's key (theft mode) |
| `restore --recovery` | Use the recovery phrase instead of the phone |

**Using real cloud storage:** the vault can be any restic repository.

- Backblaze B2: set `B2_ACCOUNT_ID` and `B2_ACCOUNT_KEY`, then use `--vault b2:your-bucket:phonekey`.
- Google Drive (via rclone): `--vault rclone:gdrive:phonekey`.

## Tests

```bash
python test_e2e.py
```

A simulated phone runs the whole story: pair, back up, deny a restore, approve a restore (the files must match byte for byte), back up from the new PC, revoke the old PC, and reject a wrong key.

## Known limits

- **The phone side is a web page, not an app yet.** The key lives in the phone browser's storage, tied to the PC's Wi-Fi address. A native Flutter app would keep it in the phone's secure chip and unlock it with a fingerprint.
- **Phone and PC talk over local Wi-Fi using plain HTTP.** The key is masked with a one-time pad that travels only inside the QR code. That's fine for a demo, but production needs an authenticated, encrypted channel.
- **It backs up one folder at a time, on demand.** App reinstall, settings capture and scheduled backups are on the roadmap.

## Roadmap

| Phase | What | Gate to move on |
| --- | --- | --- |
| Validate | Survey 50 students, waitlist | 100 waitlist signups |
| MVP beta | Windows agent, Android app, 30 testers on one campus | 20 clean test restores, no data lost |
| Launch v1 | App and settings restore, phone "essentials" copy, mobile-money payments, theft mode | 270 paying users (break-even) |
| Scale | iPhone app, campus licences, **CampusMesh** peer-to-peer campus backup | One university signed |

## Contributing

Ideas, issues and pull requests are welcome, especially from students. Good first areas:

- The Flutter phone app.
- Settings capture for popular apps.
- Translations.

See [SECURITY.md](SECURITY.md) to report a vulnerability privately.

## License

[MIT](LICENSE) © 2026 demi956
