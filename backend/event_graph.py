from collections import defaultdict

ENTITY_FIELD_TYPES = {
    "user": "user",
    "device": "device",
    "source_ip": "ip",
    "destination": "destination",
    "process": "process",
}


IGNORED_VALUES = {"", "n/a", "unknown", "unknown-device"}


def build_graph(events):
    node_event_ids = defaultdict(set)
    node_type = {}
    edge_event_ids = defaultdict(set)

    for event in events:
        entities_in_event = []
        for field, entity_type in ENTITY_FIELD_TYPES.items():
            value = event.get(field)
            if not value or value in IGNORED_VALUES:
                continue
            node_type[value] = entity_type
            node_event_ids[value].add(event["event_id"])
            entities_in_event.append(value)

        for i in range(len(entities_in_event)):
            for j in range(i + 1, len(entities_in_event)):
                pair = tuple(sorted((entities_in_event[i], entities_in_event[j])))
                edge_event_ids[pair].add(event["event_id"])

    nodes = [
        {
            "id": entity,
            "type": node_type[entity],
            "label": entity,
            "event_count": len(event_ids),
        }
        for entity, event_ids in node_event_ids.items()
    ]
    edges = [
        {
            "source": a,
            "target": b,
            "weight": len(event_ids),
            "event_ids": sorted(event_ids),
        }
        for (a, b), event_ids in edge_event_ids.items()
    ]

    nodes.sort(key=lambda n: (-n["event_count"], n["id"]))
    edges.sort(key=lambda e: (-e["weight"], e["source"], e["target"]))
    return {"nodes": nodes, "edges": edges}


if __name__ == "__main__":
    from data_loader import events_for_case, case_ids

    for case_id in case_ids():
        graph = build_graph(events_for_case(case_id))
        print(f"{case_id}: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
        for n in graph["nodes"]:
            print("  node:", n)
        for e in graph["edges"]:
            print("  edge:", e)
