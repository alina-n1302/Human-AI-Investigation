from datetime import datetime
from collections import defaultdict


def build_timeline(events):
    return sorted(events, key=lambda e: e["timestamp"])


def find_conflicts(events):
    by_user_time = defaultdict(list)
    for event in events:
        key = (event["user"], event["timestamp"])
        by_user_time[key].append(event)

    conflicts = []
    for (user, timestamp), group in by_user_time.items():
        source_ips = {e["source_ip"] for e in group}
        if len(group) > 1 and len(source_ips) > 1:
            conflicts.append(
                {
                    "user": user,
                    "timestamp": timestamp,
                    "event_ids": [e["event_id"] for e in group],
                    "conflicting_ips": sorted(source_ips),
                    "reason": "same user, same timestamp, different source IPs",
                }
            )
    return conflicts


def build_entity_links(events):
    links = defaultdict(set)
    for event in events:
        for field in ("user", "device", "source_ip", "destination", "process"):
            value = event.get(field)
            if value and value not in ("n/a", "unknown", "unknown-device"):
                links[value].add(event["event_id"])
    return {entity: sorted(event_ids) for entity, event_ids in links.items()}


if __name__ == "__main__":
    from data_loader import events_for_case

    events = events_for_case("CASE001")
    print("Timeline:")
    for e in build_timeline(events):
        print(" ", e["timestamp"], e["event_id"], e["event_type"])

    print("Conflicts:", find_conflicts(events))
    print("Entity links:", build_entity_links(events))
