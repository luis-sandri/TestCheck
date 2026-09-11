"""Política de SLA do TestCheck para não conformidades de artefatos."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from .models import NonconformitySeverity


@dataclass(frozen=True)
class SlaTarget:
    """Prazos, em dias úteis, para cada pessoa envolvida na NC."""

    correction_or_contestation_days: int
    reviewer_decision_days: int
    supervisor_decision_days: int


# Política de projeto adaptada a artefatos de teste: não é um SLA de incidente
# 24x7 de produção. Alta prioridade recebe tratamento acelerado; média e baixa
# preservam tempo suficiente para análise técnica e evidência de correção.
SLA_BY_PRIORITY: dict[NonconformitySeverity, SlaTarget] = {
    NonconformitySeverity.HIGH: SlaTarget(2, 1, 1),
    NonconformitySeverity.MEDIUM: SlaTarget(5, 2, 2),
    NonconformitySeverity.LOW: SlaTarget(10, 3, 3),
}


def target_for(priority: NonconformitySeverity | str) -> SlaTarget:
    if not isinstance(priority, NonconformitySeverity):
        priority = NonconformitySeverity(priority)
    return SLA_BY_PRIORITY[priority]


def add_business_days(start: datetime | None, days: int) -> datetime:
    """Mantém o horário e conta apenas segunda a sexta-feira.

    Feriados e horários de expediente ainda não fazem parte do MVP; isso fica
    explícito para não aparentar um calendário corporativo completo.
    """

    current = start or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current
