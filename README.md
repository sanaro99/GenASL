# GenASL — AI-Powered ASL Overlay Generator

GenASL is a proof-of-concept AI system that converts YouTube video transcripts into American Sign Language (ASL) overlays for Deaf and Hard of Hearing (DHH) viewers.

## How It Works

1. **Transcript Ingestion** — Fetches timestamped transcript segments from a YouTube video using the `youtube-transcript-api`.
2. **Semantic Matching** — Each transcript segment is encoded with a sentence-transformer model and matched against a curated set of supported ASL sentences via FAISS nearest-neighbour search.
3. **Render Plan Generation** — A render plan (JSON) is produced that maps every segment to either an ASL animation asset (`action: "ASL"`) or a plain-caption fallback (`action: "CAPTIONS"`) based on a confidence threshold.

## Repository Structure

```
asl-gen/
├── config.yaml                  # Pipeline configuration
├── requirements.txt             # Python dependencies
├── data/
│   └── supported_set_v1.csv     # Curated ASL sentence set (50 rows)
├── docs/
│   └── render_plan_schema.md    # Render plan JSON schema documentation
├── src/
│   ├── transcript_ingestion/    # YouTube transcript fetching
│   ├── matcher/                 # Semantic matching (sentence-transformers + FAISS)
│   └── pipeline/                # End-to-end orchestration
├── tests/                       # Unit and integration tests
└── logs/                        # Runtime logs (git-ignored)
```

## Prerequisites

- Python 3.10+
- pip

## Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd asl-gen

# 2. Create a virtual environment (recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt
```

## Configuration

All tuneable parameters live in `config.yaml`:

| Key | Description | Default |
|-----|-------------|---------|
| `matcher.model_name` | Sentence-transformer model for encoding | `all-MiniLM-L6-v2` |
| `matcher.confidence_threshold` | Minimum cosine-similarity score to choose ASL | `0.80` |
| `matcher.top_k` | Number of nearest neighbours to retrieve | `1` |
| `paths.supported_set` | Path to the supported sentence CSV | `data/supported_set_v1.csv` |
| `paths.faiss_index` | Path to the FAISS index binary | `data/faiss_index.bin` |
| `paths.index_metadata` | Path to the index metadata JSON | `data/index_metadata.json` |
| `paths.logs` | Directory for log files | `logs/` |

## Running the Pipeline

```bash
# Run the full pipeline for a YouTube video
python -m src.pipeline.run --video-id <YOUTUBE_VIDEO_ID>
```

## Running Tests

```bash
pytest tests/ -v
```

## Render Plan Output

The pipeline produces a **render plan** JSON file describing how to overlay ASL or captions on each segment. See [docs/render_plan_schema.md](docs/render_plan_schema.md) for the full schema specification.

## License

This project is licensed under the [GNU General Public License v3.0](LICENSE).
