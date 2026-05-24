from __future__ import annotations

from pathlib import Path

import great_expectations as gx


def validate(csv_path: str) -> bool:
    ctx = gx.get_context()
    suite = ctx.add_or_update_expectation_suite("baseline")
    batch = ctx.sources.add_or_update_pandas("ds").read_csv(csv_path)
    validator = ctx.get_validator(batch_request=batch.build_batch_request(), expectation_suite=suite)
    validator.expect_column_values_to_not_be_null("id")
    return validator.validate()["success"]
