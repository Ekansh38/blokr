# blokr

Brick your laptop. Block distracting sites behind a physical code you keep on paper. macOS only.

## Install

**1. Clone and add the alias:**

```bash
git clone https://github.com/ekansh38/blokr.git
echo 'alias blokr="noglob python3 /path/to/blokr/blokr.py"' >> ~/.zshrc
source ~/.zshrc
```

**2. Install yt-dlp (for watching work-related videos):**

```bash
brew install yt-dlp
```

## Setup (run once)

```bash
blokr setup
```

- Choose which sites to block (YouTube, AI tools, TikTok, or custom domains)
- A 40-character random code is generated and shown **once**
- Write it down. Put it somewhere physically inconvenient (bag, wallet, another room)
- The code is never stored in plaintext, only its hash is kept

## Usage

### Block
```bash
blokr block
```
Blocks your configured sites via `/etc/hosts`. No timer, stays locked until you unlock.

### Unblock
```bash
blokr unblock
```
1. Type your code manually from your paper (no paste allowed, detected and rejected)
2. Sit through a 5-minute countdown with a paragraph on why this matters
   - `Ctrl+C` at any point cancels and keeps you locked
3. Type `yes` to confirm
4. Type `YES SIR YES` to really confirm
5. Unblocked

### Open YouTube frontend
```bash
blokr yt
```
Opens [Invidious](https://inv.thepixora.com) — a YouTube frontend on a different domain, not blocked — in your browser. Use it to find a video, copy the URL, then run `blokr watch`.

### Watch a video (work use)
```bash
blokr watch <youtube-url> [quality]
```
Downloads the video via `yt-dlp` and opens it locally. No algorithm, no autoplay, no sidebar. Optional quality: `480`, `720`, `1080`, `1440`, `2160`, or `best` (default).

### Clean up downloads
```bash
blokr clean
```
Deletes all videos in `~/Downloads/blokr-watch`. Run this after you're done watching.

### Status
```bash
blokr status
```
Shows whether blokr is set up, currently locked, and which domains are being blocked.

### Reset / lost your paper
```bash
blokr setup
```
Wipes the existing code, unblocks if currently locked, and generates a new one. Write it down again.

## How it works

- Sites are blocked by redirecting domains to `127.0.0.1` in `/etc/hosts`
- Your unlock code is never stored, only a SHA-256 hash is kept in `~/.blokr/`
- Paste detection reads input character-by-character in raw terminal mode and measures keystroke intervals. Pastes arrive near-instantly and are rejected
