#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Any
from .helpers import get_logger

logger = get_logger()


class ValidationError(Exception):
    pass


class Variable():
    """A typed variable that updates automatically.

    Raises
    ------
    ValidationError if validation of `value` returns False.

    Notes
    -----
    Relies on global `logger` instance for logging. Make sure it exists before
    instantiating.
    """

    def __init__(self,
                 value: Any,
                 on_value_changed: Callable[[Variable, Any, Any], None] = None,
                 formatter: Callable[[Variable, Any], Any] = None,
                 validator: Callable[[Variable, Any], bool] = None,
                 ) -> None:
        self._on_value_changed = set()
        if on_value_changed:
            self._on_value_changed.add(on_value_changed)
        self.formatter = formatter
        self.validator = validator

        if self.validator and not self.validator(self, value):
            raise ValidationError(f"validation failed for value \"{value}\".")

        self._value = value
        self._type = type(value)

    def _on_value_changed_setter(self, value: Callable[[Variable, Any, Any], None]):
        self._on_value_changed.add(value)

    on_value_changed = property(None, _on_value_changed_setter)

    def _get_value(self) -> Any:
        return self._value

    def _set_value(self, new_value: Any) -> None:
        if self._type is None:
            raise RuntimeWarning(
                "Setting None value can result in errors later on.")
            self._type = type(new_value)  # Deferred setting of the type
        if new_value is not None:   # It is ok to set variable to None
            assert type(new_value) == self._type

        if self.validator and not self.validator(self, new_value):
            raise ValidationError(f"validation failed for value \"{new_value}\".")

        old_value = self._value
        self._value = new_value

        logger.debug(f"Variable \"{self}\" changed from {old_value} to {new_value}.")

        for callback in self._on_value_changed:
            callback(self, self._value, old_value)

    value = property(_get_value, _set_value)

    def __repr__(self):
        if self.formatter:
            try:
                return self.formatter(self, self._value)
            except TypeError as e:
                if self._value is None:
                    return "None"
                raise e
        return str(self._value)
