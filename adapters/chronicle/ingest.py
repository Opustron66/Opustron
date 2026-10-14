"""Benchmark adapter ingestion entry point."""

from chronicle.ingest.pipeline import IngestPipeline


def ingest(events):
    return IngestPipeline().process(events)
