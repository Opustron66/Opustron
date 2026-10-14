from chronicle.ingest.parsers.markdown import parse
from chronicle.ingest.pipeline import IngestPipeline


def test_markdown_events_receive_entities():
    events = IngestPipeline().process(parse("Met Alice yesterday."))
    assert events[0].entities[0].name == "Alice"
