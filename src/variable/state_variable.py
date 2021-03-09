#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Any
from enum import Enum
import logging
from . import Variable

logger = logging.getLogger(__name__)


class State(Enum):
    UNINITIALIZED = 0
    RED = 1
    YELLOW = 2
    GREEN = 3
    BLUE = 4


class StateVariable(Variable):
    """A typed variable with a state attached to it."""

    def __init__(self,
                 value: Any,
                 state: State = None,
                 on_state_change: Callable[[StateVariable, Any, Any], None] = None,
                 **kwargs):

        super().__init__(value, **kwargs)
        self._state = state or State.UNINITIALIZED

        self.on_state_change = on_state_change

    def _get_state(self):
        return self._state

    def _set_state(self, new_state):
        assert type(new_state) == State
        old_state = self._state
        self._state = new_state

        logger.debug(f"Variable \"{self}\" state changed from \"{old_state}\" to \"{new_state}\".")

        if self.on_state_change:
            self.on_state_change(self, self._state, old_state)

    state = property(_get_state, _set_state)
