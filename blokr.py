#!/usr/bin/env python3
import os
import sys
import time
import hashlib
import secrets
import string
import termios
import tty
import select
import json
import subprocess

CONFIG_DIR = os.path.expanduser("~/.blokr")
HASH_FILE = os.path.join(CONFIG_DIR, ".hash")
SITES_FILE = os.path.join(CONFIG_DIR, ".sites")
HOSTS_FILE = "/etc/hosts"
MARKER_START = "# blokr-start"
MARKER_END = "# blokr-end"

CODE_LENGTH = 40
CODE_CHARS = string.ascii_letters + string.digits
PASTE_THRESHOLD = 0.05  # seconds — paste arrives near-instantly, humans are ~150ms+

PRESET_SITES = {
    "YouTube": [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "youtubei.googleapis.com",
        "yt3.ggpht.com",
    ],
    "AI (Claude, ChatGPT, Gemini)": [
        "claude.ai",
        "chatgpt.com",
        "chat.openai.com",
        "gemini.google.com",
    ],
    "TikTok": [
        "tiktok.com",
        "www.tiktok.com",
        "vm.tiktok.com",
    ],
}

SHAME = """\
  YouTube's algorithm is engineered to maximize watch time, not your wellbeing.
  Every recommendation exists to pull you into the next video — not to help you
  learn or rest. Studies consistently link passive video consumption with reduced
  attention span, lower motivation, and higher anxiety. The 10 minutes you think
  you're taking costs you 45. You have real things to build. You went and found
  a piece of paper and typed 40 characters because some part of you knows that.
  Don't waste it.\
"""


# ── terminal helpers ──────────────────────────────────────────────────────────


def flush_stdin(fd):
    """Drain any buffered input (e.g. leftover paste chars)."""
    while select.select([sys.stdin], [], [], 0)[0]:
        os.read(fd, 4096)


def read_no_paste(prompt, mask=False):
    """
    Read a line char-by-char in raw terminal mode.
    Paste detection: if two consecutive chars arrive < PASTE_THRESHOLD apart,
    clear the buffer, warn, and force retype.
    mask=True shows * instead of the actual character.
    Raises KeyboardInterrupt on Ctrl+C.
    """
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)

    sys.stdout.write(prompt)
    sys.stdout.flush()

    result = []
    last_time = None

    try:
        tty.setraw(fd)
        while True:
            raw = os.read(fd, 1)
            now = time.time()
            ch = raw.decode("utf-8", errors="replace")

            if ch == "\x03":  # Ctrl+C
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                raise KeyboardInterrupt

            if ch in ("\r", "\n"):
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n")
                sys.stdout.flush()
                break

            if ch in ("\x7f", "\x08"):  # backspace
                if result:
                    result.pop()
                    sys.stdout.write("\b \b")
                    sys.stdout.flush()
                last_time = now
                continue

            # paste detection
            if last_time is not None and (now - last_time) < PASTE_THRESHOLD:
                flush_stdin(fd)
                result = []
                last_time = None
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
                sys.stdout.write("\n  [!] Paste detected. Type it manually.\n\n")
                sys.stdout.write(prompt)
                sys.stdout.flush()
                tty.setraw(fd)
                continue

            result.append(ch)
            sys.stdout.write("*" if mask else ch)
            sys.stdout.flush()
            last_time = now

    except KeyboardInterrupt:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        raise
    except Exception:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        raise

    return "".join(result)


# ── hosts file ────────────────────────────────────────────────────────────────


def block(domains):
    with open(HOSTS_FILE, "a") as f:
        f.write(f"\n{MARKER_START}\n")
        for d in domains:
            f.write(f"127.0.0.1 {d}\n")
        f.write(f"{MARKER_END}\n")


def unblock():
    with open(HOSTS_FILE, "r") as f:
        lines = f.readlines()
    new_lines = []
    inside = False
    for line in lines:
        if line.strip() == MARKER_START:
            inside = True
            continue
        if line.strip() == MARKER_END:
            inside = False
            continue
        if not inside:
            new_lines.append(line)
    with open(HOSTS_FILE, "w") as f:
        f.writelines(new_lines)


# ── config ────────────────────────────────────────────────────────────────────


def save_hash(code):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(HASH_FILE, "w") as f:
        f.write(hashlib.sha256(code.encode()).hexdigest())


def load_hash():
    if not os.path.exists(HASH_FILE):
        return None
    with open(HASH_FILE) as f:
        return f.read().strip()


def check_code(code):
    return hashlib.sha256(code.encode()).hexdigest() == load_hash()


def save_sites(domains):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(SITES_FILE, "w") as f:
        json.dump(domains, f)


def load_sites():
    if not os.path.exists(SITES_FILE):
        return []
    with open(SITES_FILE) as f:
        return json.load(f)


# ── commands ──────────────────────────────────────────────────────────────────


def cmd_setup():
    print("\n=== blokr setup ===\n")

    if os.path.exists(HASH_FILE):
        print("  Existing setup found. This will wipe it and generate a new code.")
        print("  (If currently locked, it will also unblock.)\n")
        ans = input("  Continue? (yes/no): ").strip().lower()
        if ans != "yes":
            print("  Cancelled.\n")
            return
        unblock()
        if os.path.exists(HASH_FILE):
            os.remove(HASH_FILE)
        if os.path.exists(SITES_FILE):
            os.remove(SITES_FILE)

    print("\n  What do you want to block? (y/n for each)\n")
    domains = []

    for label, sites in PRESET_SITES.items():
        ans = input(f"  Block {label}? (y/n): ").strip().lower()
        if ans == "y":
            domains.extend(sites)

    print("\n  Add custom domains? (one per line, blank to finish)")
    while True:
        d = input("  Domain: ").strip().lower()
        if not d:
            break
        domains.append(d)
        if not d.startswith("www."):
            domains.append("www." + d)

    if not domains:
        print("\n  No sites selected. Nothing to block.\n")
        return

    save_sites(list(dict.fromkeys(domains)))  # dedupe, preserve order

    code = "".join(secrets.choice(CODE_CHARS) for _ in range(CODE_LENGTH))
    save_hash(code)

    print("\n" + "=" * 62)
    print("  YOUR CODE — write this down NOW:")
    print()
    print(f"    {code}")
    print()
    print("  Put it somewhere physically inconvenient (bag, wallet, etc).")
    print("  It will NOT be shown again. Ever.")
    print("=" * 62 + "\n")

    input("  Press Enter once you've written it down...")
    print("\n  Setup complete. Run 'blokr block' to brick yourself.\n")


def cmd_block():
    if not os.path.exists(HASH_FILE):
        print("\n  Run 'blokr setup' first.\n")
        sys.exit(1)

    sites = load_sites()
    if not sites:
        print("\n  No sites configured. Run 'blokr setup'.\n")
        sys.exit(1)

    block(sites)
    print(f"\n  Locked. {len(sites)} domains blocked. Go do something real.\n")


def cmd_yt():
    subprocess.run(["open", "https://inv.thepixora.com"])


def cmd_unblock():
    stored = load_hash()
    if not stored:
        print("\n  Not set up. Run 'blokr setup'.\n")
        sys.exit(1)

    print("\n=== blokr unblock ===\n")

    # Step 1: code
    try:
        code = read_no_paste("  Enter code: ", mask=True)
    except KeyboardInterrupt:
        print("\n  Cancelled.\n")
        sys.exit(0)

    if not check_code(code):
        print("\n  Wrong code.\n")
        sys.exit(1)

    print("\n  Code accepted.\n")
    print("─" * 62)
    print()
    print(SHAME)
    print()
    print("─" * 62)
    print()

    # Step 2: 5-minute countdown (Ctrl+C = cancelled)
    try:
        end = time.time() + 5 * 60
        while True:
            remaining = end - time.time()
            if remaining <= 0:
                break
            m = int(remaining // 60)
            s = int(remaining % 60)
            sys.stdout.write(f"\r  Unblocking in {m}:{s:02d}... (Ctrl+C to cancel)")
            sys.stdout.flush()
            time.sleep(1)
        print("\r" + " " * 50)
    except KeyboardInterrupt:
        print("\n\n  Cancelled. Still locked.\n")
        sys.exit(0)

    print()

    # Step 3: first confirm
    try:
        ans1 = read_no_paste("  Unblock? (yes/no): ")
    except KeyboardInterrupt:
        print("\n  Cancelled. Still locked.\n")
        sys.exit(0)

    if ans1.strip().lower() != "yes":
        print("\n  Still locked.\n")
        sys.exit(0)

    print()

    # Step 4: second confirm
    try:
        ans2 = read_no_paste("  Are you really sure? Type: YES SIR YES\n  > ")
    except KeyboardInterrupt:
        print("\n  Cancelled. Still locked.\n")
        sys.exit(0)

    if ans2.strip() != "YES SIR YES":
        print("\n  Nope. Still locked.\n")
        sys.exit(0)

    unblock()
    print("\n  Unblocked. Make it count.\n")


def is_locked():
    with open(HOSTS_FILE) as f:
        return MARKER_START in f.read()


def cmd_watch(url):
    if not url:
        print("\n  Usage: blokr watch <url>\n")
        sys.exit(1)

    out_dir = os.path.expanduser("~/Downloads/blokr-watch")
    os.makedirs(out_dir, exist_ok=True)

    was_locked = is_locked()
    if was_locked:
        print("\n  Temporarily unblocking to download...")
        unblock()

    print(f"\n  Downloading: {url}")
    print(f"  Saving to:   {out_dir}\n")

    result = subprocess.run(
        [
            "yt-dlp",
            "-f",
            "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format",
            "mp4",
            "-o",
            os.path.join(out_dir, "%(title)s.%(ext)s"),
            url,
        ]
    )

    if was_locked:
        block(load_sites())
        print("\n  Re-blocked.")

    if result.returncode != 0:
        print("\n  Download failed.\n")
        sys.exit(1)

    # open most recently modified file in the folder
    files = sorted(
        [
            os.path.join(out_dir, f)
            for f in os.listdir(out_dir)
            if not f.startswith(".")
        ],
        key=os.path.getmtime,
        reverse=True,
    )
    if files:
        subprocess.run(["open", files[0]])


def cmd_status():
    setup_done = os.path.exists(HASH_FILE)
    locked = is_locked() if setup_done else False
    sites = load_sites() if setup_done else []

    print()
    print(f"  setup:   {'yes' if setup_done else 'no -- run blokr setup'}")
    if setup_done:
        print(f"  locked:  {'yes' if locked else 'no'}")
        print(f"  blocking {len(sites)} domains: {', '.join(sites[:3])}{'...' if len(sites) > 3 else ''}")
    print()


HELP = """
  blokr - brick your laptop

  commands:
    setup          first-time setup, pick sites, get your code (shown once)
    block          block your configured sites
    unblock        unblock (requires your paper code)
    watch <url>    download a youtube video and open it locally
    yt             open the YouTube frontend in your browser
    status         show current state
    help           show this message

  lost your paper? run setup again. it wipes and regenerates.
  find work videos at: https://inv.thepixora.com
"""


SUDO_COMMANDS = {"block", "unblock", "watch"}


# ── entrypoint ────────────────────────────────────────────────────────────────


def main():
    if len(sys.argv) < 2:
        print(HELP)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd in SUDO_COMMANDS and os.geteuid() != 0:
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)

    if cmd == "setup":
        cmd_setup()
    elif cmd == "block":
        cmd_block()
    elif cmd == "unblock":
        cmd_unblock()
    elif cmd == "watch":
        cmd_watch(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "yt":
        cmd_yt()
    elif cmd == "status":
        cmd_status()
    elif cmd in ("help", "--help", "-h"):
        print(HELP)
    else:
        print(f"\n  Unknown command: {cmd}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
