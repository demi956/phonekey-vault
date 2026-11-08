---
title: I built a backup where my phone is the key to my laptop
published: false
tags: opensource, security, python, showdev
cover_image:
---

*Paste everything below into a new dev.to post. Set `published: true` when you're ready.*

Every university student I know has a horror story: a stolen laptop on a bus, coffee on a keyboard the night before a deadline, or a final-year project that existed in exactly one place.

The numbers back this up. In Backblaze's 2024 survey, **84%** of computer owners said they'd backed up all their data, but only **15%** felt certain their important files were safe.

I study in Ghana, where there's an extra problem. Mobile data costs about **$0.40–$0.96 per GB**. Restoring a 200 GB laptop over mobile data would cost **$80–$192**, before you count the time: about 8 hours on average broadband here, or days on shared hostel Wi-Fi.

So I built a prototype of something different: **PhoneKey Vault**.

## The idea: your phone is the key, not the vault

My first idea was to back up the PC straight onto the phone. It doesn't work. Phones are too small, and when a bag is stolen, the phone often goes with the laptop.

So the phone holds the **key**, and the cloud holds the **encrypted data**:

- **Backups don't need the phone.** The PC backs up into an encrypted vault using its own device key.
- **The master key lives only on the phone.** It gets there inside a QR code and is never saved on the PC.
- **A new PC can't restore without the phone.** It shows a QR code, you tap **Approve** on your phone, and only then can it unlock the vault.
- **Theft mode.** If your laptop is stolen, one command (approved on your phone) removes its key, and it can never open the vault again.
- **Recovery phrase.** If the phone is gone too, a phrase you wrote down at setup works instead.

## How it's built

- **Encryption engine:** [restic](https://restic.net), a battle-tested open-source backup tool (AES-256, deduplicated, versioned). I didn't write my own crypto.
- **The trick:** restic supports several keys for the same repository. Each PC adds its own device key, and the master key can add or remove them. Theft mode is just `restic key remove`, gated behind phone approval.
- **Phone approval:** the restoring PC puts a request ID and a 64-byte one-time pad in the QR code. The phone sends back the master key XOR'd with the pad, so the key never crosses Wi-Fi unmasked. The pad itself only travelled optically.
- **Everyday key on the PC:** protected with Windows DPAPI, so only that Windows user can read it.
- **Size:** about 380 lines of standard-library Python, plus two small web pages.

An end-to-end test plays the phone and runs the whole story:

1. Pair the phone.
2. Back up a folder.
3. **Deny** a restore, and nothing changes.
4. **Approve** a restore, and the files match byte for byte.
5. Back up from the new PC.
6. Revoke the stolen PC, which is then locked out.
7. Reject a wrong key.

## What's honestly not done yet

- **The phone side is a web page.** The real version needs a native app that keeps the key in the phone's secure chip with fingerprint unlock.
- **Phone and PC talk over plain HTTP on local Wi-Fi.** The one-time pad covers the key, but production needs a proper authenticated channel.
- **It backs up one folder at a time, on demand.** App reinstall and settings restore are next.

## Where it's going

- **Three-tier restore:** essentials from the phone over USB in minutes, then projects, then everything else overnight on Wi-Fi.
- **Student pricing:** about $1.50 a month for 100 GB. Storage costs about $0.70 at that size.
- **CampusMesh (the wild idea):** students back each other up over the campus network using erasure coding. With a 10-of-30 split, files stay recoverable 99.9% of the time even if each laptop is online only 60% of the time. That gives free, fast restores with no mobile data at all.

## Try it, break it, tell me

Code, white paper and tests: **https://github.com/demi956/phonekey-vault**

I'd love feedback on:

- Would you use this?
- What would make you trust it?
- Is anyone interested in helping build the Flutter phone app?
