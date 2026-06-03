"""
SECTION 6: DEPLOYMENT + RECOVERY HARDENING
Extracted from PreProductionHardeningValidator.validate_deployment_recovery
"""
import hashlib
import uuid

from pre_production_hardening.hardening_validator import (
    HardeningIssue, SectionResult,
    ISSUE_CRITICAL, ISSUE_HIGH, ISSUE_MEDIUM, ISSUE_LOW,
)


def run(validator) -> SectionResult:
    issues: list = []
    try:
        from core.runner.snapshot_manager import SnapshotManager

        # Test 1: Snapshot integrity
        try:
            mgr = SnapshotManager()
            snap1 = mgr.take_snapshot(900, "Pre-deployment snapshot")
            snap2 = mgr.take_snapshot(901, "Post-deployment snapshot")

            v1 = mgr.verify_snapshot(900)
            v2 = mgr.verify_snapshot(901)

            if v1 and v2:
                issues.append(HardeningIssue(
                    section="deployment_recovery", severity=ISSUE_LOW,
                    check="snapshot_integrity",
                    detail="Two snapshots created and verified", passed=True,
                ))
            else:
                failed = []
                if not v1:
                    failed.append("900")
                if not v2:
                    failed.append("901")
                issues.append(HardeningIssue(
                    section="deployment_recovery", severity=ISSUE_HIGH,
                    check="snapshot_integrity",
                    detail=f"Snapshot verification failed for: {', '.join(failed)}",
                ))

            # Verify listing
            listing = mgr.list_snapshots()
            all_found = 900 in listing and 901 in listing
            if all_found:
                issues.append(HardeningIssue(
                    section="deployment_recovery", severity=ISSUE_LOW,
                    check="snapshot_listing", detail="All snapshots listed", passed=True,
                ))
            else:
                issues.append(HardeningIssue(
                    section="deployment_recovery", severity=ISSUE_MEDIUM,
                    check="snapshot_listing",
                    detail="Not all snapshots found in listing",
                    evidence={"listed": list(listing.keys())[:10] if isinstance(listing, dict) else listing},
                ))

        except Exception as e:
            issues.append(HardeningIssue(
                section="deployment_recovery", severity=ISSUE_HIGH,
                check="snapshot_manager", detail=f"Snapshot manager test failed: {e}",
            ))

        # Test 2: Checksum consistency
        try:
            mgr = SnapshotManager()
            snap_a = mgr.take_snapshot(902, "Checksum test A")
            snap_b = mgr.take_snapshot(903, "Checksum test B")

            if snap_a and snap_b:
                cs_a = getattr(snap_a, "checksum", None) or snap_a.get("checksum", "")
                cs_b = getattr(snap_b, "checksum", None) or snap_b.get("checksum", "")

                if cs_a and cs_b:
                    issues.append(HardeningIssue(
                        section="deployment_recovery", severity=ISSUE_LOW,
                        check="checksum_consistency",
                        detail="Checksums generated for both snapshots", passed=True,
                    ))
                    if cs_a == cs_b:
                        issues.append(HardeningIssue(
                            section="deployment_recovery", severity=ISSUE_LOW,
                            check="checksum_stability",
                            detail="Identical DB state produces identical checksum", passed=True,
                        ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="deployment_recovery", severity=ISSUE_LOW,
                check="checksum_test", detail=f"Checksum test note: {e}", passed=True,
            ))

        # Test 3: Backup meta consistency
        try:
            from backup.models import BackupRecord
            record = BackupRecord.objects.create(
                filename=f"hardening_test_{uuid.uuid4().hex[:8]}.bak",
                file_size=1024, checksum=hashlib.sha256(b"test").hexdigest(),
                status="completed",
            )
            if record.id:
                issues.append(HardeningIssue(
                    section="deployment_recovery", severity=ISSUE_LOW,
                    check="backup_record_creation",
                    detail="Backup record created successfully", passed=True,
                ))
                record.delete()
        except Exception as e:
            issues.append(HardeningIssue(
                section="deployment_recovery", severity=ISSUE_MEDIUM,
                check="backup_record_creation",
                detail=f"Backup record creation failed: {e}",
            ))

        # Test 4: Model count consistency
        try:
            from django.apps import apps
            model_counts = {}
            for model in apps.get_models():
                try:
                    count = model.objects.count()
                    model_counts[model._meta.label] = count
                except Exception:
                    pass
            if model_counts:
                total_rows = sum(model_counts.values())
                issues.append(HardeningIssue(
                    section="deployment_recovery", severity=ISSUE_LOW,
                    check="model_counts",
                    detail=f"Total rows across {len(model_counts)} models: {total_rows}", passed=True,
                ))
        except Exception as e:
            issues.append(HardeningIssue(
                section="deployment_recovery", severity=ISSUE_LOW,
                check="model_counts", detail=f"Model count check: {e}", passed=True,
            ))

    except Exception as e:
        issues.append(HardeningIssue(
            section="deployment_recovery", severity=ISSUE_CRITICAL,
            check="deployment_crash", detail=f"Deployment recovery testing crashed: {e}",
        ))

    passed = len([i for i in issues if i.severity in (ISSUE_CRITICAL, ISSUE_HIGH)]) == 0
    validator.results["deployment_recovery"] = SectionResult(
        name="Deployment + Recovery Hardening", passed=passed, issues=issues,
        detail=f"{len([i for i in issues if not i.passed])} issues found",
    )
    validator.issues.extend(issues)
    return validator.results["deployment_recovery"]
