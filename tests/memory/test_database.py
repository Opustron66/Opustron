from chronicle.memory.api import MemoryAPI
from chronicle.schema import Event, Source


def test_memory_api_stores_events():
    api = MemoryAPI()
    event = Event("hello", Source("test://1", "test"))
    assert api.remember(event) is event
    assert api.list_memories() == [event]
