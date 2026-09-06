import csv
import os
import random

from config import RANDOM_SEED, CASES_PER_HYPOTHESIS_TYPE

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

FIRST_NAMES = [
    "alex",
    "jordan",
    "sam",
    "taylor",
    "morgan",
    "casey",
    "riley",
    "quinn",
    "drew",
    "avery",
    "reese",
    "skyler",
    "hayden",
    "rowan",
]

DEVICE_KINDS = ["laptop", "workstation", "server", "vm"]


def _rand_user(rng):
    return f"{rng.choice(FIRST_NAMES)}{rng.randrange(10, 99)}"


def _rand_device(rng):
    return f"{rng.choice(DEVICE_KINDS)}-{rng.randrange(10, 99)}"


def _rand_office_ip(rng):
    return f"10.0.{rng.randrange(1, 9)}.{rng.randrange(2, 254)}"


def _rand_foreign_ip(rng):
    return f"{rng.choice([185, 91, 45, 103])}.{rng.randrange(1,254)}.{rng.randrange(1,254)}.{rng.randrange(1,254)}"


def _rand_date(rng, year=2026):
    month = rng.randrange(1, 13)
    day = rng.randrange(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"


def _ts(date, hour, minute):
    return f"{date} {hour:02d}:{minute:02d}:00"


def _mk(
    event_id,
    case_id,
    timestamp,
    event_type,
    user,
    device,
    ip,
    dest,
    process,
    severity,
    source,
    label,
    description,
):
    return (
        event_id,
        case_id,
        timestamp,
        event_type,
        user,
        device,
        ip,
        dest,
        process,
        severity,
        source,
        label,
        description,
    )


def generate_credential_compromise(case_id, rng):
    user, device = "admin", _rand_device(rng)
    ip = _rand_foreign_ip(rng)
    date = _rand_date(rng)
    hour = rng.randrange(0, 5)
    events = [
        _mk(
            f"{case_id}-E1",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "login_failed",
            user,
            device,
            ip,
            "vpn-gateway",
            "vpn-client",
            "medium",
            "auth_log",
            "suspicious",
            rng.choice(
                [
                    f"failed login attempt for {user} from a foreign ip address",
                    f"a foreign ip address makes several failed attempts against {user}",
                ]
            ),
        ),
        _mk(
            f"{case_id}-E2",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "login_success",
            user,
            device,
            ip,
            "vpn-gateway",
            "vpn-client",
            "high",
            "auth_log",
            "suspicious",
            f"{user} login succeeds moments later from the same foreign ip address",
        ),
        _mk(
            f"{case_id}-E3",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "process_start",
            user,
            device,
            ip,
            device,
            "powershell.exe",
            "high",
            "endpoint_log",
            "suspicious",
            "a scripting process is launched right after the login",
        ),
        _mk(
            f"{case_id}-E4",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "dns_query",
            user,
            device,
            ip,
            "c2.example",
            "powershell.exe",
            "high",
            "dns_log",
            "suspicious",
            rng.choice(
                [
                    "the process queries a domain known to be associated with malware",
                    "dns traffic is sent to a malicious c2 domain",
                ]
            ),
        ),
        _mk(
            f"{case_id}-E5",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "analyst_note",
            user,
            device,
            ip,
            "n/a",
            "n/a",
            "low",
            "analyst_notes",
            "context",
            "no maintenance window was scheduled for this system",
        ),
    ]
    return events, "credential_compromise"


def generate_legitimate_admin(case_id, rng):
    user, device = _rand_user(rng), _rand_device(rng)
    ip = _rand_office_ip(rng)
    date = _rand_date(rng)
    hour = rng.choice([0, 1, 22, 23])
    events = [
        _mk(
            f"{case_id}-E1",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "login_success",
            user,
            device,
            ip,
            "vpn-gateway",
            "vpn-client",
            "medium",
            "auth_log",
            "benign",
            f"{user} (IT admin) logs in from the internal corporate network",
        ),
        _mk(
            f"{case_id}-E2",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "process_start",
            user,
            device,
            ip,
            device,
            "powershell.exe",
            "medium",
            "endpoint_log",
            "benign",
            rng.choice(
                [
                    "powershell starts to run a scheduled patch process",
                    "a scheduled patch process begins via powershell",
                ]
            ),
        ),
        _mk(
            f"{case_id}-E3",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "dns_query",
            user,
            device,
            ip,
            "updates.company-internal.com",
            "wusa.exe",
            "low",
            "dns_log",
            "benign",
            "the process contacts the company's own internal update server",
        ),
        _mk(
            f"{case_id}-E4",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "analyst_note",
            user,
            device,
            ip,
            "n/a",
            "n/a",
            "low",
            "analyst_notes",
            "context",
            rng.choice(
                [
                    "a maintenance ticket authorizes this exact time window",
                    "an approved maintenance ticket covers this activity",
                ]
            ),
        ),
    ]
    return events, "legitimate_admin_activity"


def generate_insider_exfiltration(case_id, rng):
    user, device = _rand_user(rng), _rand_device(rng)
    ip = _rand_office_ip(rng)
    date = _rand_date(rng)
    hour = rng.randrange(9, 19)
    events = [
        _mk(
            f"{case_id}-E1",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "login_success",
            user,
            device,
            ip,
            "internal-vpn",
            "vpn-client",
            "low",
            "auth_log",
            "benign",
            f"{user} logs in normally during work hours",
        ),
        _mk(
            f"{case_id}-E2",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "file_access",
            user,
            device,
            ip,
            "client-database",
            "explorer.exe",
            "high",
            "file_audit_log",
            "suspicious",
            rng.choice(
                [
                    "an unusually large download of files occurs, outside normal job duties",
                    "files are pulled in an unusually large download, well outside normal job duties",
                ]
            ),
        ),
        _mk(
            f"{case_id}-E3",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "network_upload",
            user,
            device,
            ip,
            "personal-cloud-storage.example",
            "chrome.exe",
            "high",
            "network_log",
            "suspicious",
            "a large volume of files is uploaded to a personal cloud storage account",
        ),
        _mk(
            f"{case_id}-E4",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "analyst_note",
            user,
            device,
            ip,
            "n/a",
            "n/a",
            "medium",
            "analyst_notes",
            "context",
            "HR records show this happened just after resignation was submitted",
        ),
        _mk(
            f"{case_id}-E5",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "analyst_note",
            user,
            device,
            ip,
            "n/a",
            "n/a",
            "low",
            "analyst_notes",
            "context",
            "no ticket was found authorizing this bulk transfer",
        ),
    ]
    return events, "insider_data_exfiltration"


def generate_ambiguous(case_id, rng):
    user, device = rng.choice(["backup-svc", "monitor-svc", "sync-svc"]), _rand_device(
        rng
    )
    ip = _rand_office_ip(rng)
    date = _rand_date(rng)
    hour = rng.randrange(1, 4)
    events = [
        _mk(
            f"{case_id}-E1",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "login_success",
            user,
            device,
            ip,
            "vpn-gateway",
            "vpn-client",
            "medium",
            "auth_log",
            "benign",
            f"the {user} account logs in at an odd early-morning hour",
        ),
        _mk(
            f"{case_id}-E2",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "process_start",
            user,
            device,
            ip,
            device,
            "agent.exe",
            "medium",
            "endpoint_log",
            "benign",
            "a background process starts shortly after login",
        ),
        _mk(
            f"{case_id}-E3",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "file_access",
            user,
            device,
            ip,
            "shared-drive",
            "agent.exe",
            "medium",
            "file_audit_log",
            "benign",
            "files are touched as part of a routine-looking job",
        ),
        _mk(
            f"{case_id}-E4",
            case_id,
            _ts(date, hour, rng.randrange(0, 59)),
            "analyst_note",
            user,
            device,
            ip,
            "n/a",
            "n/a",
            "low",
            "analyst_notes",
            "context",
            "no one on the team can immediately confirm the schedule for this",
        ),
    ]
    return events, "insufficient_evidence"


GENERATORS = {
    "credential_compromise": generate_credential_compromise,
    "legitimate_admin_activity": generate_legitimate_admin,
    "insider_data_exfiltration": generate_insider_exfiltration,
    "insufficient_evidence": generate_ambiguous,
}


def generate_dataset(cases_per_type=CASES_PER_HYPOTHESIS_TYPE, seed=RANDOM_SEED):
    rng = random.Random(seed)
    all_events = []
    all_cases = []
    counter = 0
    for hyp_type, generator in GENERATORS.items():
        for i in range(cases_per_type):
            counter += 1
            case_id = f"GEN{counter:04d}"
            events, ground_truth = generator(case_id, rng)
            all_events.extend(events)
            all_cases.append(
                (
                    case_id,
                    f"generated {hyp_type} scenario #{i+1}",
                    ground_truth,
                    "auto-generated for evaluation, see case_generator.py",
                )
            )
    return all_events, all_cases


def write_generated_dataset(cases_per_type=CASES_PER_HYPOTHESIS_TYPE, seed=RANDOM_SEED):
    os.makedirs(DATA_DIR, exist_ok=True)
    events, cases = generate_dataset(cases_per_type, seed)

    event_header = [
        "event_id",
        "case_id",
        "timestamp",
        "event_type",
        "user",
        "device",
        "source_ip",
        "destination",
        "process",
        "severity",
        "source",
        "label",
        "description",
    ]
    with open(
        os.path.join(DATA_DIR, "generated_events.csv"),
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        w = csv.writer(f)
        w.writerow(event_header)
        w.writerows(events)

    case_header = ["case_id", "scenario", "ground_truth_hypothesis", "notes"]
    with open(
        os.path.join(DATA_DIR, "generated_cases.csv"), "w", newline="", encoding="utf-8"
    ) as f:
        w = csv.writer(f)
        w.writerow(case_header)
        w.writerows(cases)

    print(
        f"wrote {len(events)} events across {len(cases)} generated cases "
        f"({cases_per_type} per hypothesis type, seed={seed})"
    )


if __name__ == "__main__":
    write_generated_dataset()
