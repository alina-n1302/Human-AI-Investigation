from event_graph import build_graph


def _events(*rows):
    """Build minimal event dicts for graph tests - only the fields
    event_graph.py actually reads are required."""
    events = []
    for i, row in enumerate(rows, start=1):
        event = {
            "event_id": f"E{i:03d}",
            "user": "n/a", "device": "n/a", "source_ip": "n/a",
            "destination": "n/a", "process": "n/a",
        }
        event.update(row)
        events.append(event)
    return events


def test_two_entities_in_one_event_produce_one_edge():
    events = _events({"user": "alice", "device": "laptop-01"})
    graph = build_graph(events)
    ids = {n["id"] for n in graph["nodes"]}
    assert ids == {"alice", "laptop-01"}
    assert len(graph["edges"]) == 1
    edge = graph["edges"][0]
    assert {edge["source"], edge["target"]} == {"alice", "laptop-01"}
    assert edge["weight"] == 1
    assert edge["event_ids"] == ["E001"]


def test_repeated_co_occurrence_increases_edge_weight():
    events = _events(
        {"user": "alice", "device": "laptop-01"},
        {"user": "alice", "device": "laptop-01"},
    )
    graph = build_graph(events)
    assert len(graph["edges"]) == 1
    assert graph["edges"][0]["weight"] == 2
    assert graph["edges"][0]["event_ids"] == ["E001", "E002"]


def test_ignored_placeholder_values_produce_no_node():
    events = _events({"user": "alice", "device": "unknown-device", "source_ip": "n/a"})
    graph = build_graph(events)
    ids = {n["id"] for n in graph["nodes"]}
    assert ids == {"alice"}
    assert graph["edges"] == []


def test_node_types_match_the_originating_field():
    events = _events({"user": "alice", "source_ip": "10.0.0.15", "destination": "finance-share"})
    graph = build_graph(events)
    type_by_id = {n["id"]: n["type"] for n in graph["nodes"]}
    assert type_by_id["alice"] == "user"
    assert type_by_id["10.0.0.15"] == "ip"
    assert type_by_id["finance-share"] == "destination"


def test_event_count_reflects_how_many_events_mention_the_entity():
    events = _events(
        {"user": "alice", "device": "laptop-01"},
        {"user": "alice", "device": "laptop-02"},
    )
    graph = build_graph(events)
    counts = {n["id"]: n["event_count"] for n in graph["nodes"]}
    assert counts["alice"] == 2
    assert counts["laptop-01"] == 1
    assert counts["laptop-02"] == 1


def test_three_entities_in_one_event_are_fully_connected():
    events = _events({"user": "admin", "device": "server-01", "source_ip": "185.10.20.30"})
    graph = build_graph(events)
    pairs = {frozenset((e["source"], e["target"])) for e in graph["edges"]}
    assert pairs == {
        frozenset({"admin", "server-01"}),
        frozenset({"admin", "185.10.20.30"}),
        frozenset({"server-01", "185.10.20.30"}),
    }


def test_build_graph_on_the_real_demo_dataset_produces_a_connected_looking_graph():
    """Not a mock - runs against the actual generated demo data, the same
    way baseline.py's and ml_ranker.py's own tests exercise real events."""
    from data_loader import events_for_case

    graph = build_graph(events_for_case("CASE001"))
    assert len(graph["nodes"]) > 0
    assert len(graph["edges"]) > 0
    node_ids = {n["id"] for n in graph["nodes"]}
    for edge in graph["edges"]:
        assert edge["source"] in node_ids
        assert edge["target"] in node_ids
        assert edge["weight"] == len(edge["event_ids"])
