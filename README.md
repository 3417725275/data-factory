# data-factory

Multi-platform data scraping tool. Fetches structured content from 9 platforms, outputs per-item folders with JSON metadata.

## Quick Start

```bash
pip install -e ".[dev]"
cp config.example.yaml config.yaml  # edit with your settings

# Search
data-factory --config config.yaml search youtube "LLM tutorial" --limit 5

# Fetch
data-factory --config config.yaml fetch "https://www.youtube.com/watch?v=xxx"

# Fetch from URL list
data-factory --config config.yaml fetch --from urls.txt

# Refresh comments
data-factory --config config.yaml refresh

# Check status
data-factory --config config.yaml index status

# Rebuild index
data-factory --config config.yaml index rebuild --all

# Rerun transcription
data-factory --config config.yaml process transcribe --platform youtube

# Import from file
data-factory --config config.yaml import --platform xiaohongshu export.json

# Start scheduler
data-factory --config config.yaml schedule start
```

## Supported Platforms

| Platform | Search | Fetch | Comments | Media | Tool |
|----------|--------|-------|----------|-------|------|
| YouTube | ✅ | ✅ | ✅ | ✅ Thumbnail | opencli |
| Bilibili | ✅ | ✅ | ✅ | ✅ Cover | opencli |
| Reddit | ✅ | ✅ | ✅ | — | opencli |
| Xiaohongshu | ✅ | ✅ | ✅ | ✅ | opencli |
| Zhihu | ✅ | ✅ | ⚠️ Pending | — | opencli |
| Twitter/X | ✅ | ✅ | ✅ | ✅ | opencli |
| TikTok | ✅ | ✅ | ⚠️ Pending | ✅ yt-dlp | opencli |
| Discourse | ✅ | ✅ | ✅ | — | REST API |
| GitHub | ✅ | ✅ | ✅ | — | REST API |

## Architecture

```
Fetch → Process → Index

PlatformAdapter (ABC)
  ├── YouTubeAdapter      (opencli)
  ├── BilibiliAdapter     (opencli)
  ├── RedditAdapter       (opencli)
  ├── XiaohongshuAdapter  (opencli)
  ├── ZhihuAdapter        (opencli)
  ├── TwitterAdapter      (opencli)
  ├── TikTokAdapter       (opencli + yt-dlp)
  ├── DiscourseAdapter    (requests)
  └── GitHubAdapter       (requests)

Processor (ABC)
  ├── TranscribeProcessor (Whisper API → Local → Platform subtitle)
  └── ImageDownloadProcessor
```

## Output Structure

```
output/
├── youtube/
│   ├── index.json
│   └── <video_id>/
│       ├── meta.json          # Metadata with comments_refresh state
│       ├── description.txt
│       ├── comments.json
│       ├── transcript.json    # After transcription
│       └── assets/
│           └── thumbnail.jpg
├── reddit/
│   ├── index.json
│   └── <post_id>/
│       ├── meta.json
│       ├── content.md
│       └── comments.json
└── global_index.json
```

## Comment Refresh Strategy

Smart backoff to minimize unnecessary API calls:

1. **Daily** — initial refresh interval
2. **3 days** — after 2 consecutive unchanged checks
3. **7 days** — after 3 consecutive unchanged
4. **14 days** — after 4+ consecutive unchanged (cap)
5. Resets to daily on any change

## Configuration

Copy `config.example.yaml` to `config.yaml` and edit:

- `output_dir`: where fetched data is stored
- `transcribe.whisper_api.api_key`: OpenAI API key for transcription
- `platforms.<name>.enabled`: enable/disable platforms
- `platforms.<name>.rate_limit`: seconds between requests
- `scheduler.jobs`: cron-based scheduled tasks

Environment variable overrides:
- `DATA_FACTORY_WHISPER_API_KEY`
- `DATA_FACTORY_PROXY`
- `DATA_FACTORY_OUTPUT_DIR`

## Requirements

- Python 3.11+
- [opencli](https://github.com/nicepkg/opencli) (`npm install -g opencli`)
- yt-dlp (for video/audio download): `pip install yt-dlp`

## Development

```bash
pip install -e ".[dev]"
pytest -v
```
