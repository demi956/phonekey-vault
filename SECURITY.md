# Security policy

PhoneKey Vault is a **prototype**. Please don't rely on it as your only backup yet.

## Reporting a vulnerability

Please report security issues **privately**, not in a public issue. On GitHub, use **Security → Report a vulnerability** on this repository. You'll get a reply within 7 days.

## Known prototype limits

These are already known, so there's no need to report them:

- **Plain HTTP between phone and PC.** The phone and PC talk over local Wi-Fi without TLS. The master key is masked with a one-time pad that travels only inside a QR code.
- **Key stored in the phone browser.** The phone keeps the key in its browser's local storage, not in hardware-backed storage, and there's no biometric unlock yet.
- **Same-network requirement.** The approval server listens on port 8765 on your local network while a request is open, and only for that one request.
