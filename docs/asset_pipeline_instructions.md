# Asset Pipeline Instructions

Step-by-step guide for building the 3D ASL overlay asset library.

## Prerequisites

- Python 3.10+ with the project venv activated
- FFmpeg installed and on PATH (`ffmpeg -version` to verify)
- Internet access (for WLASL index download and YouTube clip downloads)

```bash
# Activate venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
# source .venv/bin/activate          # Linux/macOS

# Install asset pipeline dependencies
pip install yt-dlp requests
```

---

## Step 1: Download the WLASL Dataset Index

Downloads the WLASL_v0.3.json file (~2 MB) and checks how many of our 50 keywords are covered.

```bash
python scripts/download_wlasl_index.py
```

**Expected output:** Coverage report showing which keywords are found in WLASL and which will use placeholders.

**Review:** Check `data/wlasl_index.json` was created and review the coverage percentage.

---

## Step 2: Create Placeholder Clips

Generates fallback placeholder MP4 clips (blue background + white text) for any sentences that can't be sourced from WLASL.

```bash
python scripts/create_placeholder.py
```

**Expected output:** Two files in `assets/placeholders/`:
- `generic_placeholder.mp4` — "ASL signing in progress"
- `placeholder.mp4` — copy of the above

**Verify:** Open `assets/placeholders/placeholder.mp4` in any video player — should be a 2-second blue clip with white text.

---

## Step 3: Review Keyword Map (MANUAL STEP)

Before building assets, review `scripts/keyword_map.csv` to verify the ASL keyword chosen for each sentence makes sense.

Things to check:
- Is the keyword actually in WLASL? (Cross-reference with Step 1 coverage report)
- Is it the most meaningful sign for that sentence?
- Some sentences share the same keyword (e.g., S011 and S031 both use NAME) — this is intentional

Edit the CSV if needed, then re-run Step 1 to update coverage.

---

## Step 4: Build All Assets

Downloads WLASL clips, trims to the sign segment, standardizes to 320×240 @ 25fps, and falls back to placeholder when download fails.

```bash
python scripts/build_assets.py
```

**This step takes time** — it downloads up to 50 YouTube clips. Expect 10–30 minutes depending on network speed and YouTube availability.

**Expected output:**
- Clips in `assets/raw/`, `assets/trimmed/`, `assets/final/`
- Updated `assets/asset_manifest_v1.json` with source info and QA results
- Summary showing how many came from WLASL vs. placeholder

---

## Step 5: Run QA on All Clips

Verifies every clip in `assets/final/` meets the standard spec (320×240, ~25fps, 0.5–5.0s duration).

```bash
python scripts/run_qa_all.py
```

**Expected output:** QA report listing passed/failed clips with specific issues.

---

## Troubleshooting

### yt-dlp: "Unable to extract video data" or HTTP 403
YouTube frequently blocks automated downloads. Try:
1. Update yt-dlp: `pip install -U yt-dlp`
2. Use cookies: `yt-dlp --cookies-from-browser chrome ...`
3. The build_assets.py script will automatically fall back to placeholder clips

### FFmpeg not found
- Windows: `winget install FFmpeg` or download from https://ffmpeg.org/download.html
- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`
- Verify: `ffmpeg -version`

### WLASL keyword not found
- The WLASL dataset only covers ~2000 ASL glosses
- Uncommon words may not be present — they'll use placeholder clips
- You can edit `scripts/keyword_map.csv` to try alternative keywords
- Re-run Step 1 to check if the new keyword has coverage

### Download timeout or rate limiting
- YouTube may rate-limit after many downloads
- The script caches downloads in `assets/raw/` — re-running will skip already-downloaded clips
- Wait a few minutes between retries

---

## File Reference

| File | Purpose |
|------|---------|
| `scripts/keyword_map.csv` | Maps sentence_id → ASL keyword for WLASL lookup |
| `scripts/download_wlasl_index.py` | Downloads WLASL dataset JSON |
| `scripts/create_placeholder.py` | Generates fallback placeholder clips |
| `scripts/build_assets.py` | Master orchestration — downloads + processes all 50 clips |
| `scripts/trim_and_standardize.py` | Utility: download, trim, standardize, QA functions |
| `scripts/run_qa_all.py` | QA check all final clips |
| `data/wlasl_index.json` | WLASL dataset index (downloaded) |
| `assets/asset_manifest_v1.json` | Master catalog of all 50 assets |
| `assets/final/A001–A050.mp4` | Final standardized clips |
