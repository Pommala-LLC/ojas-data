"""
Ojas Fixture Validator v0.3.2

Validates positive fixtures (must pass) and negative fixtures (must fail
with specific expected error substrings).

Layout:
    fixtures/
        01_valid_read/           ... 08_raw_sql_rejected_policy_built/
            request.json
            response.json
            audit.json
            ...
            README.md (optional)
        _negative/
            request_with_sql_field/
                instance.json          - the malformed fixture
                expected_error.txt     - error substrings the validator should produce
                target.txt             - schema-label/defs-name to validate against

Each positive fixture file is validated against a specific $defs entry.
Each negative fixture is validated and MUST produce errors that include
all substrings in expected_error.txt (one per line).

Usage:
    python3 validate.py

Exit code 0 if all positive fixtures pass AND all negative fixtures fail
with the expected errors. Non-zero otherwise.
"""

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT202012
except ImportError as e:
    print(f"FATAL: missing dependency: {e}")
    print("Install with: pip install jsonschema referencing")
    sys.exit(2)


SCHEMA_DIR = Path(__file__).parent
SCHEMA_FILES = [
    "OJAS_DATA_RUNTIME_BUNDLE_SCHEMA_V0.3.2.json",
    "OJAS_RUNTIME_DATA_SCHEMA_V0.3.2.json",
    "OJAS_EVIDENCE_STORE_SCHEMA_V0.3.2.json",
]

SCHEMA_ID_BY_LABEL = {
    "bundle": "https://schemas.ojas.dev/ojas/data-runtime-bundle/v0.3.2/schema.json",
    "runtime-data": "https://schemas.ojas.dev/ojas/runtime-data/v0.3.2/schema.json",
    "evidence-store": "https://schemas.ojas.dev/ojas/evidence-store/v0.3.2/schema.json",
}


def load_schemas():
    parsed = {}
    for fname in SCHEMA_FILES:
        path = SCHEMA_DIR / fname
        with open(path) as f:
            s = json.load(f)
        parsed[s["$id"]] = s
    resources = [
        (sid, Resource(contents=s, specification=DRAFT202012))
        for sid, s in parsed.items()
    ]
    return parsed, Registry().with_resources(resources)


# ---- Positive fixture mapping ----
POSITIVE_MAPPING = {
    "01_valid_read/request.json": ("bundle", "data-execute-request"),
    "01_valid_read/response.json": ("bundle", "data-execute-response"),
    "01_valid_read/audit.json": ("evidence-store", "evidence-record"),

    "02_blocked_sensitive_field/request.json": ("bundle", "data-execute-request"),
    "02_blocked_sensitive_field/response.json": ("bundle", "data-execute-response"),
    "02_blocked_sensitive_field/audit.json": ("evidence-store", "evidence-record"),
    "02_blocked_sensitive_field/sanitized_feedback.json": ("bundle", "sanitized-feedback"),

    "03_cud_preflight_failure/request.json": ("bundle", "data-execute-request"),
    "03_cud_preflight_failure/response.json": ("bundle", "data-execute-response"),
    "03_cud_preflight_failure/audit.json": ("evidence-store", "evidence-record"),
    "03_cud_preflight_failure/preflight_orchestration.json": ("evidence-store", "evidence-record"),

    "04_destructive_delete_preexec_required/request.json": ("bundle", "data-execute-request"),
    "04_destructive_delete_preexec_required/response.json": ("bundle", "data-execute-response"),
    "04_destructive_delete_preexec_required/audit.json": ("evidence-store", "evidence-record"),
    "04_destructive_delete_preexec_required/gate_event.json": ("runtime-data", "pre-execution-gate-event"),
    "04_destructive_delete_preexec_required/gate_response.json": ("runtime-data", "pre-execution-gate-response"),
    "04_destructive_delete_preexec_required/pre_execution_audit_binding.json": ("evidence-store", "evidence-record"),

    "05_bulk_insert_signal/request.json": ("bundle", "data-execute-request"),
    "05_bulk_insert_signal/response.json": ("bundle", "data-execute-response"),
    "05_bulk_insert_signal/audit.json": ("evidence-store", "evidence-record"),
    "05_bulk_insert_signal/bulk_context_observed.json": ("evidence-store", "bulk-context-observed"),

    "06_create_after_destroy_signal/destroy_audit.json": ("evidence-store", "evidence-record"),
    "06_create_after_destroy_signal/create_audit.json": ("evidence-store", "evidence-record"),
    "06_create_after_destroy_signal/create_after_destroy_observed.json": ("evidence-store", "create-after-destroy-observed"),

    "07_policy_timeout_deny/gate_event.json": ("runtime-data", "pre-execution-gate-event"),
    "07_policy_timeout_deny/gate_response_timeout.json": ("runtime-data", "policy-response-timeout"),
    "07_policy_timeout_deny/response.json": ("bundle", "data-execute-response"),
    "07_policy_timeout_deny/audit.json": ("evidence-store", "evidence-record"),

    "08_raw_sql_rejected_policy_built/request.json": ("bundle", "sql-review-request"),
    "08_raw_sql_rejected_policy_built/response.json": ("bundle", "sql-review-response"),
    "08_raw_sql_rejected_policy_built/audit.json": ("evidence-store", "evidence-record"),
    "08_raw_sql_rejected_policy_built/sanitized_feedback.json": ("bundle", "sanitized-feedback"),
}


def validate_against_defs(instance, schema_label, defs_name, registry):
    schema_id = SCHEMA_ID_BY_LABEL[schema_label]
    pointer = {"$ref": f"{schema_id}#/$defs/{defs_name}"}
    v = Draft202012Validator(pointer, registry=registry)
    return list(v.iter_errors(instance))


def _format_error(e) -> str:
    path = "/".join(str(p) for p in e.absolute_path) or "(root)"
    return f"{path}: {e.message}"


def validate_positive(fixtures_dir: Path, registry):
    """Each positive fixture must validate cleanly."""
    results = []
    for relpath, (label, defs_name) in sorted(POSITIVE_MAPPING.items()):
        path = fixtures_dir / relpath
        if not path.exists():
            results.append((relpath, label, defs_name, "MISSING", []))
            continue
        try:
            with open(path) as f:
                instance = json.load(f)
        except json.JSONDecodeError as e:
            results.append((relpath, label, defs_name, "BAD_JSON", [str(e)]))
            continue
        errors = validate_against_defs(instance, label, defs_name, registry)
        if errors:
            results.append((relpath, label, defs_name, "FAIL",
                            [_format_error(e) for e in errors]))
        else:
            results.append((relpath, label, defs_name, "OK", []))
    return results


def validate_negative(fixtures_dir: Path, registry):
    """Each negative fixture must produce errors covering all expected substrings."""
    neg_dir = fixtures_dir / "_negative"
    if not neg_dir.exists():
        return []
    results = []
    for child in sorted(neg_dir.iterdir()):
        if not child.is_dir():
            continue
        instance_path = child / "instance.json"
        target_path = child / "target.txt"
        expected_path = child / "expected_error.txt"
        missing = [n for n, p in (
            ("instance.json", instance_path),
            ("target.txt", target_path),
            ("expected_error.txt", expected_path),
        ) if not p.exists()]
        if missing:
            results.append((child.name, "INCOMPLETE", missing, None))
            continue
        target = target_path.read_text().strip()
        if "/" not in target:
            results.append((child.name, "BAD_TARGET",
                            [f"target.txt must be 'schema-label/defs-name', got: {target!r}"],
                            None))
            continue
        label, defs_name = target.split("/", 1)
        if label not in SCHEMA_ID_BY_LABEL:
            results.append((child.name, "BAD_TARGET",
                            [f"unknown schema label: {label}"], None))
            continue
        try:
            with open(instance_path) as f:
                instance = json.load(f)
        except json.JSONDecodeError as e:
            results.append((child.name, "BAD_JSON", [str(e)], None))
            continue
        errors = validate_against_defs(instance, label, defs_name, registry)
        if not errors:
            # Negative fixture didn't fail — that's a problem
            results.append((child.name, "UNEXPECTED_PASS",
                            ["Negative fixture passed validation; must fail."], None))
            continue
        # Check expected substrings
        expected_lines = [l.strip() for l in expected_path.read_text().splitlines()
                          if l.strip() and not l.strip().startswith("#")]
        error_text = "\n".join(_format_error(e) for e in errors)
        missing_subs = [sub for sub in expected_lines if sub not in error_text]
        if missing_subs:
            results.append((child.name, "WRONG_FAILURE",
                            [f"Expected error substring not found: {sub!r}"
                             for sub in missing_subs] +
                            [f"Actual errors: {error_text[:500]}"], None))
        else:
            results.append((child.name, "OK_FAILS_AS_EXPECTED",
                            [], len(errors)))
    return results


def main():
    print("=" * 64)
    print("Ojas Fixture Validator v0.3.2")
    print("=" * 64)

    parsed, registry = load_schemas()
    print(f"Loaded {len(parsed)} schemas with cross-file $ref registry")
    print()

    fixtures_dir = SCHEMA_DIR / "fixtures"
    if not fixtures_dir.exists():
        print(f"ERROR: no fixtures directory at {fixtures_dir}")
        sys.exit(2)
    print(f"Fixtures: {fixtures_dir}")
    print()

    # Positive
    print("-" * 64)
    print("POSITIVE FIXTURES (must pass)")
    print("-" * 64)
    pos = validate_positive(fixtures_dir, registry)
    pos_stats = {"OK": 0, "FAIL": 0, "MISSING": 0, "BAD_JSON": 0}
    for relpath, label, defs_name, status, errors in pos:
        pos_stats[status] = pos_stats.get(status, 0) + 1
        marker = {"OK": "OK", "FAIL": "FAIL", "MISSING": "MISS", "BAD_JSON": "BAD!"}[status]
        print(f"  [{marker:4s}] {relpath}  ->  {label}/{defs_name}")
        if errors:
            for err in errors[:3]:
                print(f"          {err[:240]}")
            if len(errors) > 3:
                print(f"          ... +{len(errors)-3} more")

    # Negative
    print()
    print("-" * 64)
    print("NEGATIVE FIXTURES (must fail with expected errors)")
    print("-" * 64)
    neg = validate_negative(fixtures_dir, registry)
    neg_stats = {}
    for name, status, errors, err_count in neg:
        neg_stats[status] = neg_stats.get(status, 0) + 1
        marker_map = {
            "OK_FAILS_AS_EXPECTED": "PASS",
            "UNEXPECTED_PASS": "FAIL",
            "WRONG_FAILURE": "FAIL",
            "BAD_JSON": "BAD!",
            "BAD_TARGET": "BAD!",
            "INCOMPLETE": "INC ",
        }
        marker = marker_map.get(status, "????")
        extra = f"  ({err_count} schema errors as expected)" if err_count else ""
        print(f"  [{marker}] _negative/{name} -- {status}{extra}")
        if errors:
            for err in errors[:3]:
                print(f"          {err[:240]}")
            if len(errors) > 3:
                print(f"          ... +{len(errors)-3} more")

    print()
    print("=" * 64)
    print(f"Positive: {pos_stats}")
    print(f"Negative: {neg_stats}")
    print("=" * 64)

    pos_clean = (pos_stats.get("FAIL", 0) == 0 and
                 pos_stats.get("MISSING", 0) == 0 and
                 pos_stats.get("BAD_JSON", 0) == 0)
    neg_clean = all(s == "OK_FAILS_AS_EXPECTED" for _, s, _, _ in neg)
    if pos_clean and neg_clean:
        print("All fixtures clean.")
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
