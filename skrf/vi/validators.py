from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Sequence

import re
from abc import ABC, abstractmethod
from enum import Enum


class ValidationError(Exception):
    pass


class Validator(ABC):
    @abstractmethod
    def validate_input(self, arg) -> Any:
        """Try to convert arg to a valid value and return. Used to ensure
        commands sent to the instrument are the proper format."""
        pass

    def validate_output(self, arg) -> Any:
        """Try to convert arg to a valid value and return. Used to convert
        responses from the instrument to something useful. By default,
        this just calls validate_input, but can be overwritten in subclasses.
        (See EnumValidator)"""
        return self.validate_input(arg)


class IntValidator(Validator):
    def __init__(self, min: int | None = None, max: int | None = None) -> None:
        self.min = min
        self.max = max

    def validate_input(self, arg) -> int:
        try:
            arg = int(arg)
        except ValueError:
            raise ValidationError(f"Could not convert {arg} to an int")

        if self.min is not None or self.max is not None:
            self.check_bounds(arg)

        return arg

    def check_bounds(self, arg):
        try:
            if self.min is not None:
                assert arg >= self.min
        except AssertionError:
            raise ValidationError(f"{arg} < {self.min}")

        try:
            if self.max is not None:
                assert arg <= self.max
        except AssertionError:
            raise ValidationError(f"{arg} > {self.max}")


class FloatValidator(Validator):
    def __init__(self, min: float | None = None, max: float | None = None) -> None:
        self.min = min
        self.max = max

    def validate_input(self, arg) -> float:
        try:
            arg = float(arg)
        except ValueError:
            raise ValidationError(f"Could not convert {arg} to a float")

        if self.min is not None or self.max is not None:
            self.check_bounds(arg)

        return arg

    def check_bounds(self, arg):
        try:
            if self.min is not None:
                assert arg >= self.min
        except AssertionError:
            raise ValidationError(f"{arg} < {self.min}")

        try:
            if self.max is not None:
                assert arg <= self.max
        except AssertionError:
            raise ValidationError(f"{arg} > {self.max}")


class FreqValidator(Validator):
    freq_re = re.compile(r"(?P<val>\d+\.?\d*)\s*(?P<si_prefix>[kMG])?(?:[hH][zZ])?")
    si = {"k": 1e3, "M": 1e6, "G": 1e9}

    def validate_input(self, arg) -> int:
        if isinstance(arg, str):
            f = re.fullmatch(self.freq_re, arg)
            if f is None:
                raise ValidationError("Invalid frequency string")
            return int(float(f["val"]) * self.si.get(f["si_prefix"], 1))

        else:
            try:
                return int(arg)
            except ValueError:
                raise ValidationError("Could not convert {arg} to an int")


class EnumValidator(Validator):
    def __init__(self, enum: Enum) -> None:
        self.Enum = enum

    def validate_input(self, arg) -> Any:
        if isinstance(arg, Enum):
            return arg.value
        else:
            try:
                return self.Enum(arg).value
            except ValueError:
                raise ValidationError(f"{arg} is not a valid {self.Enum.__name__}")

    def validate_output(self, arg) -> Any:
        try:
            return self.Enum(arg)
        except ValueError:
            raise ValidationError(f"Got unexpected response {arg}")


class SetValidator(Validator):
    def __init__(self, valid: Sequence) -> None:
        dtype = type(valid[0])
        if not all(isinstance(x, dtype) for x in valid):
            raise ValueError("All elements of set must be of the same type.")

        self.valid = valid
        self.dtype = dtype

    def validate_input(self, arg) -> Any:
        arg = self.dtype(arg)
        if arg in self.valid:
            return arg
        else:
            raise ValidationError(f"{arg} is not in {self.valid}")


class DictValidator(Validator):
    def __init__(self, arg_string: str, response_pattern: re.Pattern | str) -> None:
        self.arg_string = arg_string
        if isinstance(response_pattern, str):
            self.pattern = re.compile(response_pattern)
        else:
            self.pattern = response_pattern

    def validate_input(self, arg) -> str:
        try:
            return self.arg_string.format(**arg)
        except KeyError as e:
            raise ValidationError(f"Missing expected argument '{e}'")

    def validate_output(self, arg) -> dict:
        match = self.pattern.fullmatch(arg)
        if match:
            return match.groupdict()
        else:
            raise ValidationError(
                f"Response did not fit regex. Response: {arg} Pattern: {self.pattern.pattern}"
            )
