import csv
import io
import itertools

REQUIRED_COLUMNS = [
    "timestamp",
    "event_type",
    "user",
    "device",
    "source_ip",
    "destination",
    "process",
    "severity",
    "source",
    "description",
]

MAX_EVENTS_PER_UPLOAD = 2000

_uploaded_cases = {}
_next_case_number = itertools.count(1)


class UploadError(ValueError):
    pass


def _read_text(file_stream):
    raw = file_stream.read()
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig", errors="replace")
    return raw


def parse_upload(file_stream, filename):
    text = _read_text(file_stream)
    if not text.strip():
        raise UploadError("that file is empty")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise UploadError(
            "couldn't find a header row - the first line should list column names"
        )

    missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
    if missing:
        raise UploadError(
            "missing required column(s): "
            + ", ".join(missing)
            + " - see the README for the expected format"
        )

    case_id = f"UPLOAD{next(_next_case_number):03d}"
    events = []
    for i, row in enumerate(reader, start=1):
        if i > MAX_EVENTS_PER_UPLOAD:
            raise UploadError(
                f"that file has more than {MAX_EVENTS_PER_UPLOAD} rows - trim it down and try again"
            )
        events.append(
            {
                "event_id": (row.get("event_id") or "").strip()
                or f"{case_id}-E{i:03d}",
                "case_id": case_id,
                "timestamp": row["timestamp"].strip(),
                "event_type": row["event_type"].strip(),
                "user": row["user"].strip(),
                "device": row["device"].strip(),
                "source_ip": row["source_ip"].strip(),
                "destination": row["destination"].strip(),
                "process": row["process"].strip(),
                "severity": row["severity"].strip() or "unknown",
                "source": row["source"].strip(),
                "label": (row.get("label") or "").strip() or "unlabeled",
                "description": row.get("description", "").strip(),
            }
        )

    if not events:
        raise UploadError("that file doesn't have any data rows below the header")

    _uploaded_cases[case_id] = {"events": events, "filename": filename}
    return case_id


def list_uploaded_cases():
    return [
        {
            "case_id": case_id,
            "scenario": f"uploaded file: {data['filename']}",
            "ground_truth_hypothesis": "",
            "notes": "user-uploaded data - there's no known correct answer to check this against",
        }
        for case_id, data in _uploaded_cases.items()
    ]


def is_uploaded_case(case_id):
    return case_id in _uploaded_cases


def events_for_uploaded_case(case_id):
    data = _uploaded_cases.get(case_id)
    return data["events"] if data else []
