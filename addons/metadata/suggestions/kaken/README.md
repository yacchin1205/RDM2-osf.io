# KAKEN Suggestion Service

## Overview

A service that indexes researcher data from KAKEN (科学研究費助成事業データベース) into Elasticsearch and provides input completion for researcher and research project information based on e-Rad IDs.

Due to the large volume of KAKEN data, the system uses ResourceSync protocol for incremental synchronization, periodically fetching only changes to reduce system load while maintaining up-to-date data.

## Architecture

```
KAKEN ResourceSync (nrid.nii.ac.jp)
    ↓
ResourceSync Client → Transformer → Elasticsearch (kaken_researchers)
                                            ↑
                                    Suggestion API (kaken:erad, kaken:kenkyusha_shimei)
```

## Key Components

### 1. Data Synchronization
- **ResourceSync Client** (`client.py`): Fetches KAKEN data
- **Transformer** (`transformer.py`): Converts data formats
- **Elasticsearch Service** (`elasticsearch.py`): Index management and search

### 2. Celery Tasks
- **sync_kaken_data**: Periodic data synchronization (daily at 2:00 UTC)
- **cleanup_old_sync_logs**: Old log cleanup (weekly on Sunday at 3:00 UTC)

### 3. Suggestion API
- **suggest_kaken()**: Searches KAKEN data based on user input

## Configuration

```python
# Defined in addons/metadata/settings/local.py

# Elasticsearch connection settings for storing KAKEN data
KAKEN_ELASTIC_URI = 'elasticsearch:9200'
KAKEN_ELASTIC_INDEX = 'kaken_researchers'

# Maximum number of documents to fetch from KAKEN ResourceSync URL per update
KAKEN_SYNC_MAX_DOCUMENTS_PER_EXECUTION = 10000
```

## Usage

**Production Environment**: Automatically synchronized (daily at 2:00 UTC). No manual operations required.

**Development Environment**: Manual execution required due to Celery Beat not being defined.

### Manual Execution in Development
```bash
# Data synchronization (automatically creates index if it doesn't exist)
docker compose run --rm web python3 -m scripts.update_kaken

# Dry run (for testing)
docker compose run --rm web python3 -m scripts.update_kaken --dry-run
```

### Suggestion Configuration
```json
{
  "key": "kaken:erad",
  "template": "<div>{{kenkyusha_shimei}}<small>{{erad}} - {{kenkyukikan_mei}} - {{kadai_mei}} (KAKEN)</small></div>",
  "autofill": {
    "number": "erad",
    "name_ja": "kenkyusha_shimei_ja_msfullname",
    "name_en": "kenkyusha_shimei_en_msfullname"
  }
}
```

See `website/project/metadata/e-rad-metadata-1.json` for details.

## Testing

```bash
docker compose run --rm web invoke test_module -n 1 -m addons/metadata/tests/test_kaken_suggestion.py
```