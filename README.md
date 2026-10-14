# Chronicle

Chronicle is a temporal memory and reasoning toolkit organized into ingestion,
memory, reasoning, privacy, and integration layers.

## Development

```powershell
python -m pip install -e ".[dev]"
pytest
```

The current implementation is an intentionally small, importable foundation.
Each layer has a clear boundary for the P1-P4 implementation work.
