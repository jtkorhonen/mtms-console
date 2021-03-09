#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Any
import asyncio
from .helpers import get_logger
from . import Variable, State, StateVariable

logger = get_logger()


class AutomaticStateVariable(StateVariable):
    """A typed state variable with automatic state control."""

    def __init__(self,
                 value: Any,
                 green_to_yellow: float = None,
                 yellow_to_red: float = None,
                 **kwargs):
        super().__init__(value, **kwargs)

        if green_to_yellow is not None:
            self._green_to_yellow = float(green_to_yellow)
            logger.debug(f"green-to-yellow timeout in \"{self}\" set to {self._green_to_yellow} s.")
        else:
            self._green_to_yellow = None
        self._green_to_yellow_handle = None

        if yellow_to_red is not None:
            self._yellow_to_red = float(yellow_to_red)
            logger.debug(f"yellow-to-red timeout in \"{self}\" set to {self._yellow_to_red} s.")
        else:
            self._yellow_to_red = None
        self._yellow_to_red_handle = None

    @property
    def green_to_yellow(self):
        return self._green_to_yellow

    @green_to_yellow.setter
    def green_to_yellow(self, new_value):
        if new_value is None:
            self._green_to_yellow = None
        else:
            self._green_to_yellow = float(new_value)
            logger.debug(f"green-to-yellow timeout in \"{self}\" set to {self._green_to_yellow} s.")

    @property
    def yellow_to_red(self):
        return self._yellow_to_red

    @yellow_to_red.setter
    def yellow_to_red(self, new_value):
        if new_value is None:
            self._yellow_to_red = None
        else:
            self._yellow_to_red = float(new_value)
            logger.debug(f"yellow-to-red timeout in \"{self}\" set to {self._yellow_to_red} s.")

    def _set_state(self, new_state: State) -> None:
        super()._set_state(new_state)

        # Cancel existing callbacks
        if (self._green_to_yellow_handle and    # noqa: W504
                not self._green_to_yellow_handle.cancelled()):
            self._green_to_yellow_handle.cancel()

        if (self._yellow_to_red_handle and    # noqa: W504
                not self._yellow_to_red_handle.cancelled()):
            self._yellow_to_red_handle.cancel()

        if new_state == State.GREEN and self.green_to_yellow:
            loop = asyncio.get_running_loop()

            self._green_to_yellow_handle = loop.call_later(
                self.green_to_yellow,
                lambda self: self._set_state(State.YELLOW), self)

        if new_state == State.YELLOW and self.yellow_to_red:
            loop = asyncio.get_running_loop()

            self._yellow_to_red_handle = loop.call_later(
                self.yellow_to_red,
                lambda self: self._set_state(State.RED), self)

    state = property(StateVariable._get_state, _set_state)

    def _set_value(self, new_value: Any) -> None:
        super()._set_value(new_value)
        self.state = State.GREEN

    value = property(Variable._get_value, _set_value)
