# Render Plan JSON Schema

The **render plan** is the primary output of the GenASL pipeline. It describes, segment by segment, how a YouTube video's transcript should be presented — either as an ASL animation overlay or as plain captions.

## Top-Level Fields

| Field | Type | Description |
|-------|------|-------------|
| `run_id` | `string` | Unique identifier for this pipeline run (UUID v4). |
| `video_id` | `string` | YouTube video ID that was processed. |
| `generated_at` | `string` | ISO 8601 timestamp of when the render plan was generated. |
| `total_segments` | `integer` | Total number of transcript segments processed. |
| `asl_segments` | `integer` | Number of segments matched to an ASL asset (`action: "ASL"`). |
| `captions_segments` | `integer` | Number of segments that fell back to captions (`action: "CAPTIONS"`). |
| `segments` | `array` | Ordered list of segment objects (see below). |

## Segment Object Fields

| Field | Type | Description |
|-------|------|-------------|
| `segment_id` | `integer` | Zero-based index of the segment within the transcript. |
| `start_ms` | `integer` | Start time of the segment in milliseconds from the beginning of the video. |
| `end_ms` | `integer` | End time of the segment in milliseconds from the beginning of the video. |
| `text` | `string` | Original transcript text for this segment. |
| `action` | `string` | Either `"ASL"` (render the matched ASL asset) or `"CAPTIONS"` (render plain captions). |
| `sentence_id` | `string \| null` | The `sentence_id` from the supported set that was matched, or `null` if no confident match was found. |
| `score` | `number` | Cosine-similarity score from the FAISS search (0.0–1.0). |

## Fallback Rule

> If the best match score is **below the confidence threshold** (default `0.80`), the segment falls back to captions:
>
> - `action` → `"CAPTIONS"`
> - `sentence_id` → `null`

Segments that meet or exceed the threshold receive:
- `action` → `"ASL"`
- `sentence_id` → the ID of the matched sentence from the supported set

## Example

```json
{
  "run_id": "b3f1a2c4-5678-4d90-abcd-ef1234567890",
  "video_id": "dQw4w9WgXcQ",
  "generated_at": "2026-02-25T12:00:00Z",
  "total_segments": 3,
  "asl_segments": 2,
  "captions_segments": 1,
  "segments": [
    {
      "segment_id": 0,
      "start_ms": 0,
      "end_ms": 3200,
      "text": "Hello everyone and welcome to the channel.",
      "action": "ASL",
      "sentence_id": "S001",
      "score": 0.94
    },
    {
      "segment_id": 1,
      "start_ms": 3200,
      "end_ms": 7500,
      "text": "Today we are going to learn about photosynthesis.",
      "action": "CAPTIONS",
      "sentence_id": null,
      "score": 0.62
    },
    {
      "segment_id": 2,
      "start_ms": 7500,
      "end_ms": 11000,
      "text": "Let's get started.",
      "action": "ASL",
      "sentence_id": "S012",
      "score": 0.88
    }
  ]
}
```
