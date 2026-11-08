"""End-to-end test: pair, back up, restore on a "new PC" with phone approval, deny, revoke.

A simulated phone talks to the approval server exactly like phone.html does.
Uses its own temp folders and a fake LOCALAPPDATA, so real settings are untouched.
"""

import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from phonekey import find_restic  # noqa: E402

API = "http://127.0.0.1:8765"
RESTIC = find_restic()   # resolved with the real LOCALAPPDATA before the test overrides it


def b64u(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def unb64u(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def get(path):
    with urllib.request.urlopen(API + path, timeout=5) as r:
        return r.status, r.read()


def post(path, body):
    req = urllib.request.Request(API + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=5) as r:
        return json.loads(r.read())


class Phone:
    """Stands in for the phone's browser: keeps the master key, approves or denies."""
    key = None

    def act(self, decision="approve"):
        for _ in range(100):
            try:
                pc = json.loads(get("/api/pc")[1])
                break
            except OSError:
                time.sleep(0.2)
        else:
            raise RuntimeError("approval server never came up")
        url = urllib.parse.urlparse(pc["qr"])
        frag = urllib.parse.parse_qs(url.fragment)
        status, html = get(url.path)
        assert status == 200 and b"PhoneKey" in html, "phone page not served"
        req = frag["req"][0]
        if pc["kind"] == "pair":
            self.key = frag["k"][0]
            assert pc["phrase"] == self.key
            post("/api/paired", {"req": req})
        elif decision == "deny":
            post("/api/approve", {"req": req, "deny": True})
        else:
            pad = unb64u(frag["pad"][0])
            ct = bytes(a ^ b for a, b in zip(self.key.encode(), pad))
            post("/api/approve", {"req": req, "ct": b64u(ct)})


def run(pc_home, *args, phone=None, decision="approve", expect_ok=True):
    env = dict(os.environ, LOCALAPPDATA=str(pc_home), PHONEKEY_RESTIC=RESTIC)
    cmd = [sys.executable, str(HERE / "phonekey.py"), "--bind", "127.0.0.1", "--host", "127.0.0.1",
           "--no-browser", *args]
    t = None
    if phone:
        t = threading.Thread(target=phone.act, args=(decision,), daemon=True)
        t.start()
    r = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=300)
    if t:
        t.join(10)
    ok = r.returncode == 0
    print(f"  {'OK ' if ok == expect_ok else 'FAIL'} phonekey {' '.join(args)}  (exit {r.returncode})")
    if ok != expect_ok:
        print(r.stdout, r.stderr)
        sys.exit(1)
    return r


def main():
    root = Path(tempfile.mkdtemp(prefix="phonekey-test-"))
    old_pc, new_pc = root / "old-pc", root / "new-pc"
    vault, docs, restored = root / "vault", root / "Documents", root / "restored"
    for d in (old_pc, new_pc, docs / "Thesis", docs / "node_modules"):
        d.mkdir(parents=True)
    (docs / "Thesis" / "chapter1.docx").write_bytes(os.urandom(200_000))
    (docs / "notes.txt").write_text("Final-year project notes\n")
    (docs / "node_modules" / "junk.js").write_text("skip me")
    phone = Phone()
    try:
        print("1. Create vault and pair phone")
        run(old_pc, "init", "--vault", str(vault), phone=phone)
        cfg = json.loads((old_pc / "PhoneKey" / "config.json").read_text())
        assert phone.key not in json.dumps(cfg), "master key leaked into the PC's config"
        print("  OK  master key is not stored on the PC")

        print("2. Back up Documents on the old PC")
        run(old_pc, "backup", str(docs))

        print("3. New PC: phone denies the restore")
        run(new_pc, "restore", "--vault", str(vault), "--to", str(restored), phone=phone,
            decision="deny", expect_ok=False)
        assert not restored.exists(), "files restored despite denial"

        print("4. New PC: phone approves the restore")
        run(new_pc, "restore", "--vault", str(vault), "--to", str(restored), phone=phone)
        assert (restored / "notes.txt").read_text() == "Final-year project notes\n"
        assert (restored / "Thesis" / "chapter1.docx").read_bytes() == (docs / "Thesis" / "chapter1.docx").read_bytes()
        assert not (restored / "node_modules").exists(), "junk folder was backed up"
        print("  OK  files match, junk skipped")

        print("5. New PC can now back up on its own")
        (docs / "notes.txt").write_text("edited on the new PC\n")
        run(new_pc, "backup", str(docs))

        print("6. Theft mode: new PC revokes the old PC's key, with phone approval")
        run(new_pc, "revoke", cfg["device_key_id"][:8], phone=phone)
        run(old_pc, "snapshots", expect_ok=False)
        print("  OK  old PC is locked out")

        print("7. Wrong key is rejected")
        wrong = Phone()
        wrong.key = "x" * 43
        run(root / "thief-pc", "restore", "--vault", str(vault), "--to", str(root / "thief"), phone=wrong,
            expect_ok=False)
        print("\nAll checks passed.")
    finally:
        shutil.rmtree(root, ignore_errors=True)


if __name__ == "__main__":
    main()
