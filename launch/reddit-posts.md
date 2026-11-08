# Reddit posts

Read each subreddit's rules before posting; some only allow self-promotion on certain days. Post to one subreddit a day, not all at once.

## r/selfhosted

**Title:** I built a restic-based backup where your phone holds the master key and approves restores

**Body:**

> I'm a student in Ghana and wanted a backup my friends would actually use, one that survives the laptop being stolen. PhoneKey Vault wraps restic:
>
> - Each PC gets its own restic key (protected with DPAPI) for everyday backups.
> - The master key lives only on your phone. It gets there by QR code.
> - A new PC can't restore until you tap Approve on your phone.
> - A stolen PC's key can be removed from the repository ("theft mode").
>
> The repository can be a local folder, B2 or rclone, so it works with whatever storage you already self-host.
>
> It's a prototype (the phone side is a web page for now), with an end-to-end test and a white paper. I'd love feedback from people who run restic for real: https://github.com/demi956/phonekey-vault

## r/SideProject

**Title:** My first prototype: a backup app where your phone is the key to your laptop

**Body:**

> Students around me keep losing laptops, along with the only copy of their projects. So I built PhoneKey Vault:
>
> - Your PC backs up into an encrypted vault.
> - Your phone holds the key.
> - Restoring on a new PC needs your phone's approval.
>
> It's planned around expensive mobile data, which costs $0.40–$0.96/GB here in Ghana: essentials first, the rest overnight on Wi-Fi.
>
> There's a working prototype, tests and a white paper. Feedback very welcome: https://github.com/demi956/phonekey-vault

## r/opensource

**Title:** PhoneKey Vault: open-source (MIT) phone-keyed PC backup built on restic, looking for contributors

**Body:**

> A working prototype in about 380 lines of Python. The next big piece is a Flutter phone app that keeps the key in Android Keystore / iOS Secure Enclave with fingerprint unlock. Good first issues include settings capture for popular apps and translations.
>
> https://github.com/demi956/phonekey-vault
