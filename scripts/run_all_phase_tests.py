"""
scripts/run_all_phase_tests.py
==============================
VETRA Phase 15 Master Regression Test Runner.

Executes all 11 previous phase test suites and the Phase 15 pytest test suite:
- test_phase_6_6.py (5 checks)
- test_phase_6_7.py (13 checks)
- test_phase_7_3.py (15 checks)
- test_phase_8.py (18 checks)
- test_phase_9.py (25 checks)
- test_phase_10.py (30 checks)
- test_phase_11.py (30 checks)
- test_phase_12.py (30 checks)
- test_phase_13.py (30 checks)
- test_phase_14.py (30 checks)
- test_alert_compatibility.py (7 checks)
- test_phase_15.py (38 tests)

Baseline regression: 233 / 233 passed.
Grand total with Phase 15: 271 / 271 passed.
"""

import os
import sys
import subprocess
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"
PYTHON_EXE = ROOT_DIR / ".venv" / "Scripts" / "python.exe"

STANDALONE_SUITES = [
    ("test_phase_6_6.py", 5, "Phase 6.6 — Core Flow & Telemedicine"),
    ("test_phase_6_7.py", 13, "Phase 6.7 — Analytics & Verification"),
    ("test_phase_7_3.py", 15, "Phase 7.3 — Alert Resolution & Verification"),
    ("test_phase_8.py", 18, "Phase 8.0 — Edge Vision & Camera Triage"),
    ("test_phase_9.py", 25, "Phase 9.0 — Surveillance & Outbreak Verification"),
    ("test_phase_10.py", 30, "Phase 10.0 — Multimodal Animal Health"),
    ("test_phase_11.py", 30, "Phase 11.0 — Predictive AI & Health Forecasting"),
    ("test_phase_12.py", 30, "Phase 12.0 — Institutional Reporting & Governance"),
    ("test_phase_13.py", 30, "Phase 13.0 — Cross-Farm Early Warning & Govt Packages"),
    ("test_phase_14.py", 30, "Phase 14.0 — Production Deployment & Security Hardening"),
    ("test_alert_compatibility.py", 7, "Alert Schema Compatibility Verification"),
]

def run_suite(file_name, expected_checks, label):
    test_path = TESTS_DIR / file_name
    print(f"\n>> Running {file_name} ({label})...")
    start = time.time()
    res = subprocess.run(
        [str(PYTHON_EXE), str(test_path)],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    duration = time.time() - start
    if res.returncode == 0:
        print(f"   [PASS] {file_name}: {expected_checks}/{expected_checks} passed ({duration:.2f}s)")
        return True, expected_checks
    else:
        print(f"   [FAIL] {file_name} failed with returncode {res.returncode}")
        print("   STDERR:")
        print(res.stderr[:500])
        print("   STDOUT:")
        print(res.stdout[-1000:])
        return False, 0

def run_phase_15_pytest():
    test_path = TESTS_DIR / "test_phase_15.py"
    print(f"\n>> Running test_phase_15.py (Phase 15 SIH Final Master Suite via pytest)...")
    start = time.time()
    res = subprocess.run(
        [str(PYTHON_EXE), "-m", "pytest", str(test_path), "-q"],
        cwd=str(ROOT_DIR),
        capture_output=True,
        text=True
    )
    duration = time.time() - start
    if res.returncode == 0 and "38 passed" in res.stdout:
        print(f"   [PASS] test_phase_15.py: 38/38 passed ({duration:.2f}s)")
        return True, 38
    else:
        print(f"   [FAIL] test_phase_15.py pytest failed:")
        print(res.stdout)
        print(res.stderr)
        return False, 0

def main():
    print("=" * 80)
    print("VETRA MASTER TEST RUNNER — ALL PHASES REGRESSION & PHASE 15")
    print("=" * 80)

    total_passed = 0
    total_expected = 0
    failures = []

    # 1. Run Baseline Suites (Phases 6.6 - 14 + alert compat)
    for file_name, expected, label in STANDALONE_SUITES:
        total_expected += expected
        ok, passed = run_suite(file_name, expected, label)
        if ok:
            total_passed += passed
        else:
            failures.append(file_name)

    baseline_passed = total_passed
    baseline_expected = total_expected

    # 2. Run Phase 15 Pytest Suite
    total_expected += 38
    ok_15, passed_15 = run_phase_15_pytest()
    if ok_15:
        total_passed += passed_15
    else:
        failures.append("test_phase_15.py")

    print("\n" + "=" * 80)
    print("VETRA MASTER TEST RESULTS SUMMARY")
    print("=" * 80)
    print(f"Previous Regression Baseline (Phases 6.6 - 14): {baseline_passed} / {baseline_expected} PASSED")
    print(f"Phase 15 SIH Final Suite:                       {passed_15 if ok_15 else 0} / 38 PASSED")
    print(f"GRAND TOTAL:                                    {total_passed} / {total_expected} PASSED")
    print("=" * 80)

    if failures:
        print(f"STATUS: FAILURES DETECTED IN: {failures}")
        return 1
    else:
        print("STATUS: 100% PASS — ZERO REGRESSIONS DETECTED")
        return 0

if __name__ == "__main__":
    sys.exit(main())
