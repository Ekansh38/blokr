# blokr

Block distracting sites locally for a set amount of time. macOS only.

## Usage

```bash
sudo python3 blokr.py
```

Follow the prompts:
1. Enter hours and minutes for the block duration
2. Choose what to block:
   - `1` — YouTube
   - `2` — AI sites (Claude, ChatGPT, Gemini)
   - `3` — Both

The script blocks the sites via `/etc/hosts`, prints a countdown every minute, and automatically unblocks when the time is up. Press `Ctrl+C` to unblock early.

## Setup (run once)

Add the alias to your shell:

```bash
echo 'alias blokr="sudo python3 /path/to/blokr.py"' >> ~/.zshrc
source ~/.zshrc
```

Then just run:

```bash
blokr
```
