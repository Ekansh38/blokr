#!/usr/bin/env python3
import time
import sys

HOSTS_FILE = "/etc/hosts"
REDIRECT = "127.0.0.1"
MARKER_START = "# blokr-start"
MARKER_END = "# blokr-end"

SITES = {
    "youtube": [
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
        "youtu.be",
    ],
    "ai": [
        "claude.ai",
        "chatgpt.com",
        "chat.openai.com",
        "gemini.google.com",
    ],
}


def block(domains):
    with open(HOSTS_FILE, "a") as f:
        f.write(f"\n{MARKER_START}\n")
        for domain in domains:
            f.write(f"{REDIRECT} {domain}\n")
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


def main():
    print("=== blokr ===\n")

    # Time input
    try:
        hours = int(input("Hours (0 if none): ").strip() or "0")
        minutes = int(input("Minutes (0 if none): ").strip() or "0")
    except ValueError:
        print("Invalid input.")
        sys.exit(1)

    total_minutes = hours * 60 + minutes
    if total_minutes <= 0:
        print("Enter a time greater than 0.")
        sys.exit(1)

    # Site selection
    print("\nWhat to block?")
    print("  1) YouTube")
    print("  2) AI (Claude, ChatGPT, Gemini)")
    print("  3) Both")
    choice = input("\nChoice (1/2/3): ").strip()

    if choice == "1":
        domains = SITES["youtube"]
    elif choice == "2":
        domains = SITES["ai"]
    elif choice == "3":
        domains = SITES["youtube"] + SITES["ai"]
    else:
        print("Invalid choice.")
        sys.exit(1)

    print(f"\nBlocking for {hours}h {minutes}m... (requires sudo)")
    block(domains)

    end_time = time.time() + total_minutes * 60
    try:
        while True:
            remaining = end_time - time.time()
            if remaining <= 0:
                break
            mins_left = -(-int(remaining) // 60)  # ceiling division
            print(f"  {mins_left} min remaining")
            time.sleep(60)
    except KeyboardInterrupt:
        print("\nInterrupted — unblocking...")

    unblock()
    print("Done. Sites unblocked.")


if __name__ == "__main__":
    main()
