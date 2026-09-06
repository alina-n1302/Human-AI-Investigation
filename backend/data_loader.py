import csv
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _read_csv(filename):
    path = os.path.join(DATA_DIR, filename)
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_events():
    return _read_csv("events.csv")


def load_entities():
    return _read_csv("entities.csv")


def load_cases():
    return _read_csv("cases.csv")


def events_for_case(case_id):
    return [e for e in load_events() if e["case_id"] == case_id]


def case_ids():
    return sorted({e["case_id"] for e in load_events()})


def load_generated_events():
    return _read_csv("generated_events.csv")


def load_generated_cases():
    return _read_csv("generated_cases.csv")


if __name__ == "__main__":
    events = load_events()
    print(f"Loaded {len(events)} events across cases: {case_ids()}")
    print("First event:", events[0])
