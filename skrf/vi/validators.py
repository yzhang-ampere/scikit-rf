"""
.. module:: skrf.vi.validators
==============================
validators (:mod:`skrf.vi.validators`)
==============================

.. autosummary::
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Optional, Sequence, Union

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
    def __init__(self, min: Optional[int] = None, max: Optional[int] = None) -> None:
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
    def __init__(self, min: Optional[float] = None, max: Optional[float] = None) -> None:
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

    def validate_output(self, arg) -> int:
        try:
            f = float(arg)
            return int(f)
        except ValueError:
            raise ValidationError(f"Response from instrument ({arg}) could not be converted to an int")


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
    def __init__(self, arg_string: str, response_pattern: Union[re.Pattern, str]) -> None:
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
                "Response did not fit regex. "
                f"Response: {arg} Pattern: {self.pattern.pattern}"
            )

class DelimitedStrValidator(Validator):
    def __init__(self, dtype: type =str , sep: str = ',') -> None:
        self.dtype = dtype
        self.sep = sep

    def validate_input(self, arg: Sequence) -> str:
        if not all(isinstance(x, self.dtype) for x in arg):
            raise ValidationError("All elements must be of type {self.dtype}.")

        return self.sep.join(str(x) for x in arg)

    def validate_output(self, arg: str) -> list:
        arg = arg.replace('"', '')
        return [self.dtype(val) for val in arg.split(self.sep)]

class BooleanValidator(Validator):
    truthy = ['1', 'on', 'true']
    falsey = ['0', 'off', 'false']

    def __init__(
        self, 
        true_response: Optional[str] = None, 
        false_response: Optional[str] = None, 
        true_setting: str='1', 
        false_setting: str='0'
    ):
        if true_response:
            self.truthy.append(true_response.lower())
        if false_response:
            self.falsey.append(false_response.lower())

        self.true_val = true_setting
        self.false_val = false_setting

    def validate_input(self, arg) -> str:
        if str(arg).lower() in self.truthy:
            return self.true_val
        elif str(arg).lower() in self.falsey:
            return self.false_val
        else:
            raise ValidationError('Argument must be a truthy or falsey value')

    def validate_output(self, arg) -> bool:
        return str(arg).lower() in self.truthy