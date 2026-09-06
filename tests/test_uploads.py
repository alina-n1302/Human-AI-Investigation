import io

import uploads


HEADER = "timestamp,event_type,user,device,source_ip,destination,process,severity,source,description"


def _csv(*rows, header=HEADER):
    """Build an in-memory CSV file the same shape parse_upload() expects."""
    text = header + "\n" + "\n".join(rows)
    return io.BytesIO(text.encode("utf-8"))


def _minimal_row(**overrides):
    row = {
        "timestamp": "2021-05-06 12:00:00",
        "event_type": "login",
        "user": "jdoe",
        "device": "vpn-gw-01",
        "source_ip": "203.0.113.5",
        "destination": "internal-network",
        "process": "n/a",
        "severity": "high",
        "source": "vpn_logs",
        "description": "single-factor login using a leaked VPN password",
    }
    row.update(overrides)
    return ",".join(row[col] for col in HEADER.split(","))


def _assert_raises(exc_type, fn, *args, match=None):
    """This project's other test files check exceptions with a plain
    try/except (see test_ml_ranker.py's holdout test) instead of
    pytest.raises, so uploads' tests follow the same style."""
    try:
        fn(*args)
        assert False, f"expected {exc_type.__name__}"
    except exc_type as e:
        if match is not None:
            assert match in str(e), f"expected {match!r} in error message, got {e!r}"


def test_valid_upload_is_parsed_and_stored():
    uploads._uploaded_cases.clear()
    case_id = uploads.parse_upload(_csv(_minimal_row()), "sample.csv")
    assert case_id.startswith("UPLOAD")
    assert uploads.is_uploaded_case(case_id)

    events = uploads.events_for_uploaded_case(case_id)
    assert len(events) == 1
    event = events[0]
    assert event["case_id"] == case_id
    assert event["user"] == "jdoe"
    assert event["event_id"] == f"{case_id}-E001"   # generated, since the CSV had no event_id column
    assert event["label"] == "unlabeled"            # generated, since the CSV had no label column


def test_uploaded_case_appears_in_list_with_no_ground_truth():
    uploads._uploaded_cases.clear()
    case_id = uploads.parse_upload(_csv(_minimal_row()), "sample.csv")
    listed = uploads.list_uploaded_cases()
    assert len(listed) == 1
    assert listed[0]["case_id"] == case_id
    assert listed[0]["ground_truth_hypothesis"] == ""
    assert "sample.csv" in listed[0]["scenario"]


def test_missing_required_column_is_rejected():
    bad_header = HEADER.replace("source_ip,", "")
    bad_row = _minimal_row().replace("203.0.113.5,", "")
    _assert_raises(
        uploads.UploadError,
        uploads.parse_upload, _csv(bad_row, header=bad_header), "bad.csv",
        match="source_ip",
    )


def test_empty_file_is_rejected():
    _assert_raises(uploads.UploadError, uploads.parse_upload, io.BytesIO(b""), "empty.csv")


def test_header_only_file_is_rejected():
    _assert_raises(
        uploads.UploadError,
        uploads.parse_upload, io.BytesIO((HEADER + "\n").encode("utf-8")), "header_only.csv",
        match="data rows",
    )


def test_no_header_row_is_rejected():
    # A single data-only line with no matching column names at all means
    # DictReader can't find any of the required columns.
    _assert_raises(
        uploads.UploadError,
        uploads.parse_upload, io.BytesIO(b"just one column\n"), "no_header.csv",
    )


def test_row_with_explicit_event_id_and_label_is_kept_as_is():
    uploads._uploaded_cases.clear()
    header = "event_id,label," + HEADER
    row = "E999,suspicious," + _minimal_row()
    case_id = uploads.parse_upload(_csv(row, header=header), "labeled.csv")
    event = uploads.events_for_uploaded_case(case_id)[0]
    assert event["event_id"] == "E999"
    assert event["label"] == "suspicious"


def test_too_many_rows_is_rejected():
    rows = [_minimal_row() for _ in range(uploads.MAX_EVENTS_PER_UPLOAD + 1)]
    _assert_raises(
        uploads.UploadError,
        uploads.parse_upload, _csv(*rows), "too_big.csv",
        match=str(uploads.MAX_EVENTS_PER_UPLOAD),
    )


def test_unknown_case_id_is_not_an_uploaded_case():
    assert uploads.is_uploaded_case("CASE001") is False
    assert uploads.events_for_uploaded_case("does-not-exist") == []


def test_each_upload_gets_a_distinct_case_id():
    uploads._uploaded_cases.clear()
    first = uploads.parse_upload(_csv(_minimal_row()), "a.csv")
    second = uploads.parse_upload(_csv(_minimal_row()), "b.csv")
    assert first != second
    assert uploads.is_uploaded_case(first)
    assert uploads.is_uploaded_case(second)
