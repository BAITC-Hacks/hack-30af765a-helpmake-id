"""Shared Pydantic validator mixins.

Add reusable cross-field validators here. Each mixin is a pydantic.BaseModel
subclass. Combine with multiple inheritance::

    class MySchema(DateRangeValidatorMixin, MyBase):
        ...
"""

import datetime

import pydantic


class DateRangeValidatorMixin(pydantic.BaseModel):
    """Ensures that start_date <= end_date when both are present."""

    start_date: datetime.date | None = None
    end_date: datetime.date | None = None

    @pydantic.model_validator(mode='after')
    def validate_date_range(self) -> 'DateRangeValidatorMixin':
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise ValueError('start_date must not be later than end_date')
        return self
