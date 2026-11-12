"""Evaluation harness package for Multilingual News Intelligence Platform."""


class LegacyEvaluationDisabled(RuntimeError):
    """Raised when an old benchmark cannot produce valid project evidence."""


def legacy_evaluation_disabled(name: str) -> None:
    raise LegacyEvaluationDisabled(
        f"{name} is disabled: it uses an unvalidated or synthetic benchmark. "
        "Use the Slice 09 evaluation after the corpus and held-out queries are frozen."
    )
