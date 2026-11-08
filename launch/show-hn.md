# Show HN post

Post at https://news.ycombinator.com/submit. Weekday mornings US time (about 1–3 pm in Ghana) tend to get the most readers.

**Title** (stay under 80 characters):

```
Show HN: PhoneKey Vault – encrypted PC backup where your phone holds the key
```

**URL:**

```
https://github.com/demi956/phonekey-vault
```

**First comment** (post this yourself right after submitting):

```
Hi HN, I'm a university student in Ghana. Friends keep losing laptops (and the
only copy of their projects), and mobile data here costs $0.40–$0.96/GB, so a
cloud restore of a whole laptop is slow and expensive.

PhoneKey Vault is a prototype where the phone holds the master key rather than
the data:

- Backups use restic. Each PC has its own restic key (protected with Windows
  DPAPI), so everyday backups don't need the phone.
- The master key reaches the phone in a QR code's URL fragment and is never
  written to the PC's disk.
- Restoring on a new PC: the PC shows a QR code with a request ID and a 64-byte
  one-time pad. The phone returns key XOR pad, the PC unmasks it, restores,
  and enrols its own device key.
- Theft mode is `restic key remove` on the stolen PC's key, gated by phone
  approval.

Known gaps (in SECURITY.md): the phone side is a web page, not a native app
with Keystore and biometrics yet, and phone<->PC is plain HTTP on the LAN (the
pad only protects the key). The plan for production is a Noise/TLS channel
seeded from the QR code.

The longer-term idea is restoring around scarce bandwidth: essentials from the
phone over USB, the rest overnight, and eventually peer-to-peer campus backup
with erasure coding.

I'd really value criticism of the key handling and the threat model (it's in
docs/WHITEPAPER.md).
```
