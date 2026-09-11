from datetime import UTC, datetime

from app.models import NonconformitySeverity
from app.sla import add_business_days, target_for


def test_sla_targets_follow_the_project_priority_policy() -> None:
    assert target_for(NonconformitySeverity.HIGH).correction_or_contestation_days == 2
    assert target_for("MEDIUM").reviewer_decision_days == 2
    assert target_for("LOW").supervisor_decision_days == 3


def test_business_days_skip_the_weekend() -> None:
    friday = datetime(2026, 9, 11, 14, 30, tzinfo=UTC)

    assert add_business_days(friday, 1) == datetime(2026, 9, 14, 14, 30, tzinfo=UTC)
    assert add_business_days(friday, 2) == datetime(2026, 9, 15, 14, 30, tzinfo=UTC)
