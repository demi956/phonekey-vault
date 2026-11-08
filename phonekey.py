"""PhoneKey Vault prototype.

Backs up a folder into an encrypted restic vault. The vault has two kinds of key:
  - a device key, kept on this PC (protected with Windows DPAPI), used for everyday backups;
  - the master key, which never touches this PC's disk: it goes to your phone via a QR code
    (and to a recovery phrase you write down). A restore on a new PC needs the phone's approval.

Commands:
  python phonekey.py init --vault DIR        create a vault and pair your phone
  python phonekey.py backup FOLDER           back up a folder (uses this PC's device key)
  python phonekey.py snapshots               list backups in the vault
  python phonekey.py restore --to DIR [--vault DIR] [--recovery]
                                             restore the latest backup; asks the phone to approve
  python phonekey.py keys                    list the vault's keys (one per paired PC)
  python phonekey.py revoke KEY_ID           "theft mode": remove a lost PC's key, with phone approval

Prototype only: the phone side is a web page served by this PC over your Wi-Fi.
"""

import argparse
import base64
import ctypes
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import webbrowser
from ctypes import wintypes
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8765
CONFIG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "PhoneKey"
CONFIG_FILE = CONFIG_DIR / "config.json"
DEFAULT_EXCLUDES = ["node_modules", "__pycache__", ".venv", "*.tmp", "Thumbs.db"]
HERE = Path(__file__).resolve().parent


# ---------- small helpers ----------

def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def unb64u(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def find_restic() -> str:
    found = os.environ.get("PHONEKEY_RESTIC") or shutil.which("restic")
    if found:
        return found
    # winget may install it as Packages\restic.restic_*\restic_<version>_windows_amd64.exe without a PATH alias.
    winget = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet"
    for exe in sorted(winget.glob("Links/restic.exe")) + sorted(winget.glob("Packages/restic.restic_*/restic*.exe")):
        return str(exe)
    sys.exit("restic was not found. Install it with:  winget install restic.restic")


def run_restic(repo: str, password: str, args: list, capture=False, check=True):
    env = dict(os.environ, RESTIC_PASSWORD=password)
    result = subprocess.run([find_restic(), "-r", repo, *args], env=env, text=True,
                            capture_output=capture)
    if check and result.returncode != 0:
        detail = (result.stderr or "").strip() if capture else ""
        sys.exit(f"restic {args[0]} failed (exit {result.returncode}). {detail}")
    return result


def lan_ip() -> str:
    # Picks the address of the network card that reaches the internet; nothing is sent.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        try:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except OSError:
            return "127.0.0.1"


# ---------- Windows DPAPI: keeps the device key readable only by this Windows user ----------

class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _dpapi(data: bytes, protect: bool) -> bytes:
    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = _Blob(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = _Blob()
    fn = ctypes.windll.crypt32.CryptProtectData if protect else ctypes.windll.crypt32.CryptUnprotectData
    if not fn(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(ctypes.cast(blob_out.pbData, ctypes.c_void_p))


def save_config(repo: str, device_password: str, key_id: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps({
        "repo": repo,
        "device_key": b64u(_dpapi(device_password.encode(), protect=True)),
        "device_key_id": key_id,
        "pc_name": socket.gethostname(),
        "paired_at": datetime.now().isoformat(timespec="seconds"),
    }, indent=2))


def load_config():
    if not CONFIG_FILE.exists():
        return None
    cfg = json.loads(CONFIG_FILE.read_text())
    cfg["device_password"] = _dpapi(unb64u(cfg["device_key"]), protect=False).decode()
    return cfg


def require_config():
    cfg = load_config()
    if not cfg:
        sys.exit("This PC isn't linked to a vault yet. Run 'init' (new vault) or 'restore' (existing vault).")
    return cfg


def add_device_key(repo: str, unlock_password: str) -> tuple:
    """Adds a fresh key for this PC to the vault and returns (password, key id)."""
    device_password = secrets.token_urlsafe(32)
    fd, tmp = tempfile.mkstemp(prefix="pk-", suffix=".txt")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(device_password)
        run_restic(repo, unlock_password, ["key", "add", "--new-password-file", tmp,
                                           "--host", socket.gethostname()], capture=True)
    finally:
        os.remove(tmp)
    keys = json.loads(run_restic(repo, device_password, ["key", "list", "--json"], capture=True).stdout)
    key_id = next(k["id"] for k in keys if k.get("current"))
    return device_password, key_id


# ---------- the local approval server (the phone talks to this over Wi-Fi) ----------

class Session:
    """One pairing or approval request, shared between the CLI and the web server."""

    def __init__(self, kind: str, phone_host: str, detail: str, master: str = None):
        self.kind = kind                      # "pair", "restore" or "revoke"
        self.detail = detail                  # shown on the phone
        self.req = secrets.token_urlsafe(9)
        self.master = master                  # only set while pairing
        self.pad = secrets.token_bytes(64)    # one-time pad, travels only inside the QR code
        self.phone_host = phone_host
        self.done = threading.Event()
        self.status = "waiting"
        self.result = None
        self.created = datetime.now().strftime("%H:%M:%S")

    def phone_url(self) -> str:
        base = f"http://{self.phone_host}:{PORT}/phone"
        if self.kind == "pair":
            # The master key rides in the URL fragment (#...), which browsers never send to a server.
            return f"{base}/pair#req={self.req}&k={self.master}"
        return f"{base}/approve#req={self.req}&pad={b64u(self.pad)}"


SESSION = None


def page(name: str) -> bytes:
    return (HERE / "web" / name).read_bytes()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code: int, body: bytes, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj):
        self._send(code, json.dumps(obj).encode())

    def _from_this_pc(self) -> bool:
        return self.client_address[0] in ("127.0.0.1", "::1")

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/" and self._from_this_pc():
            return self._send(200, page("pc.html"), "text/html; charset=utf-8")
        if path == "/api/pc" and self._from_this_pc():
            s = SESSION
            return self._json(200, {"kind": s.kind, "qr": s.phone_url(), "status": s.status,
                                    "detail": s.detail,
                                    "phrase": s.master if s.kind == "pair" else None})
        if path in ("/phone/pair", "/phone/approve"):
            return self._send(200, page("phone.html"), "text/html; charset=utf-8")
        if path == "/api/request":
            s = SESSION
            return self._json(200, {"kind": s.kind, "detail": s.detail, "pc": socket.gethostname(),
                                    "created": s.created, "status": s.status})
        self._json(404, {"error": "not found"})

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            return self._json(400, {"error": "bad json"})
        s = SESSION
        if body.get("req") != s.req or s.status != "waiting":
            return self._json(409, {"error": "This request has expired. Scan the new QR code on the PC."})
        if path == "/api/paired" and s.kind == "pair":
            s.status, s.result = "approved", True
            s.done.set()
            return self._json(200, {"ok": True})
        if path == "/api/approve" and s.kind in ("restore", "revoke"):
            if body.get("deny"):
                s.status = "denied"
                s.done.set()
                return self._json(200, {"ok": True})
            ct = unb64u(body.get("ct", ""))
            if not ct or len(ct) > len(s.pad):
                return self._json(400, {"error": "bad key"})
            s.result = bytes(a ^ b for a, b in zip(ct, s.pad)).decode()
            s.status = "approved"
            s.done.set()
            return self._json(200, {"ok": True})
        self._json(404, {"error": "not found"})


def ask_phone(kind: str, detail: str, args, master: str = None, timeout=600):
    """Shows a QR code on this PC and waits until the phone approves. Returns the session."""
    global SESSION
    host = args.host or lan_ip()
    SESSION = Session(kind, host, detail, master)
    server = ThreadingHTTPServer((args.bind, PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{PORT}/"
    print(f"\nScan the QR code shown at {url} with your phone's camera.")
    print(f"(Phone and PC must be on the same Wi-Fi. Phone address: http://{host}:{PORT})")
    if not args.no_browser:
        webbrowser.open(url)
    ok = SESSION.done.wait(timeout)
    time.sleep(1.5)   # let the PC page show the final status
    server.shutdown()
    server.server_close()
    if not ok:
        sys.exit("Timed out waiting for the phone.")
    if SESSION.status != "approved":
        sys.exit("The phone denied the request. Nothing was changed.")
    return SESSION


# ---------- commands ----------

def cmd_init(args):
    if load_config():
        sys.exit(f"This PC is already linked to a vault ({CONFIG_FILE}).")
    repo = args.vault
    master = secrets.token_urlsafe(32)
    print(f"Creating encrypted vault at {repo} ...")
    run_restic(repo, master, ["init"], capture=True)
    device_password, key_id = add_device_key(repo, master)
    save_config(repo, device_password, key_id)
    print("Vault created. This PC has its own device key (protected by Windows).")
    print("Now pair your phone: it will hold the master key. Write down the recovery phrase too.")
    ask_phone("pair", f"Pair vault {repo}", args, master=master)
    del master
    print("\nPhone paired. The master key is now only on your phone and in your recovery phrase.")


def cmd_backup(args):
    cfg = require_config()
    folder = str(Path(args.folder).resolve())
    if not Path(folder).is_dir():
        sys.exit(f"Folder not found: {folder}")
    excludes = [x for e in DEFAULT_EXCLUDES for x in ("--exclude", e)]
    print(f"Backing up {folder} ...")
    run_restic(cfg["repo"], cfg["device_password"],
               ["backup", folder, "--tag", "phonekey", "--exclude-caches", *excludes])


def cmd_snapshots(args):
    cfg = require_config()
    run_restic(cfg["repo"], cfg["device_password"], ["snapshots"])


def cmd_keys(args):
    cfg = require_config()
    print(f"This PC's key id: {cfg['device_key_id'][:8]}")
    run_restic(cfg["repo"], cfg["device_password"], ["key", "list"])


def unlock_with_phone(repo: str, kind: str, detail: str, args) -> str:
    if args.recovery:
        import getpass
        return getpass.getpass("Recovery phrase: ").replace(" ", "").strip()
    session = ask_phone(kind, detail, args)
    return session.result


def cmd_restore(args):
    cfg = load_config()
    repo = args.vault or (cfg and cfg["repo"])
    if not repo:
        sys.exit("Tell me where the vault is:  restore --vault DIR --to DIR")
    target = Path(args.to).resolve()
    master = unlock_with_phone(repo, "restore",
                               f"Restore latest backup to {target} on {socket.gethostname()}", args)
    if run_restic(repo, master, ["cat", "config"], capture=True, check=False).returncode != 0:
        sys.exit("That key doesn't open this vault. Nothing was restored.")
    snaps = json.loads(run_restic(repo, master, ["snapshots", "latest", "--json"], capture=True).stdout)
    if not snaps:
        sys.exit("The vault has no backups yet.")
    snap = snaps[-1]
    source = snap["paths"][0]
    # restic names Windows paths like /C/Users/...; restore that folder's contents straight into the target.
    inner = "/" + source.replace(":", "").replace("\\", "/")
    print(f"Restoring {source} (backup from {snap['time'][:16].replace('T', ' ')}) into {target} ...")
    run_restic(repo, master, ["restore", f"{snap['short_id']}:{inner}", "--target", str(target)])
    if not cfg:
        device_password, key_id = add_device_key(repo, master)
        save_config(repo, device_password, key_id)
        print("This PC now has its own device key, so it can keep backing up to the vault.")
    del master
    print("Restore complete.")


def cmd_revoke(args):
    cfg = require_config()
    if cfg["device_key_id"].startswith(args.key_id):
        sys.exit("That's this PC's own key. Revoke it from another PC.")
    master = unlock_with_phone(cfg["repo"], "revoke", f"Remove PC key {args.key_id} from the vault", args)
    run_restic(cfg["repo"], master, ["key", "remove", args.key_id])
    del master
    print(f"Key {args.key_id} removed. That PC can no longer open the vault.")


def main():
    sys.stdout.reconfigure(line_buffering=True)   # keep our messages in order with restic's output
    p = argparse.ArgumentParser(description="PhoneKey Vault prototype")
    p.add_argument("--host", help="address the phone uses to reach this PC (default: auto-detect)")
    p.add_argument("--bind", default="0.0.0.0", help=argparse.SUPPRESS)
    p.add_argument("--no-browser", action="store_true", help="don't open the QR page automatically")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init", help="create a vault and pair your phone")
    s.add_argument("--vault", required=True, help="vault location: a folder, or any restic repository")
    s = sub.add_parser("backup", help="back up a folder")
    s.add_argument("folder")
    sub.add_parser("snapshots", help="list backups")
    sub.add_parser("keys", help="list the vault's keys")
    s = sub.add_parser("restore", help="restore the latest backup (phone approval)")
    s.add_argument("--to", required=True, help="folder to restore into")
    s.add_argument("--vault", help="vault location (needed on a new PC)")
    s.add_argument("--recovery", action="store_true", help="use the recovery phrase instead of the phone")
    s = sub.add_parser("revoke", help="remove a lost PC's key (phone approval)")
    s.add_argument("key_id")
    s.add_argument("--recovery", action="store_true", help="use the recovery phrase instead of the phone")
    args = p.parse_args()
    {"init": cmd_init, "backup": cmd_backup, "snapshots": cmd_snapshots, "keys": cmd_keys,
     "restore": cmd_restore, "revoke": cmd_revoke}[args.cmd](args)


if __name__ == "__main__":
    main()
