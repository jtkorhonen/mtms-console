#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import logging
from enum import Enum
from typing import Optional, Callable
import asyncio
from .helpers import validate_url

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    UNDEFINED = -1
    DISCONNECTED = 0
    CONNECTED = 1
    DISCONNECTING = 2
    CONNECTING = 3
    CANCELLING = 4


class ServerConnection():
    """Bogus server connection model.
    """

    def __init__(self,
                 url: Optional[str] = None,
                 on_connection_status_changed: Callable[[ServerConnection, ConnectionStatus, ConnectionStatus], None] = None
                 ):
        self._url = validate_url(url)

        self._on_connection_status_changed = set()
        if on_connection_status_changed:
            self._on_connection_status_changed.add(on_connection_status_changed)

        self._connection_status = ConnectionStatus.DISCONNECTED
        self._connect_task = None
        self._disconnect_task = None

        logger.debug(f"Initialized ServerConnection \"{self}\" with url=\"{self._url}\".")

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = validate_url(value)

    def _on_connection_status_changed_setter(self, value):
        self._on_connection_status_changed.add(value)

    on_connection_status_changed = property(None, _on_connection_status_changed_setter)

    @property
    def connection_status(self):
        return self._connection_status

    @connection_status.setter
    def connection_status(self, value: ConnectionStatus):
        old_value = self._connection_status
        self._connection_status = value

        for callback in self._on_connection_status_changed:
            callback(self, value, old_value)

    @property
    def connected(self):
        return self.connection_status in (ConnectionStatus.CONNECTED, ConnectionStatus.DISCONNECTING)

    @property
    def connecting(self):
        return self.connection_status == ConnectionStatus.CONNECTING
        # return self._connect_task is not None

    async def connect(self) -> bool:
        logger.info(f"Connecting to server \"{self.url}\"...")
        self.connection_status = ConnectionStatus.CONNECTING

        if self.url is None:
            self.connection_status = ConnectionStatus.DISCONNECTED
            logger.error("Could not initiate connection. URL is not set.")
            raise ConnectionError("Could not initiate connection. URL is not set.")

        if self._connect_task is not None:
            logger.error("Could not initiate another connection. Connection process is already started.")
            raise ConnectionError("Please disconnect or cancel the current connection attempt first.")

        async def connect_coro():
            # Bogus connection method
            await asyncio.sleep(5)
            return True

        self._connect_task = asyncio.create_task(connect_coro())
        await self._connect_task

        try:
            if self._connect_task.result():
                logger.info("Connection success.")
                self.connection_status = ConnectionStatus.CONNECTED
                self._connect_task = None
                return True
            else:
                logger.error("Connection failed.")
                self.connection_status = ConnectionStatus.DISCONNECTED
                self._connect_task = None
                return False
        except asyncio.CancelledError:
            logger.info("Connection cancelled during the process.")
            self.connection_status = ConnectionStatus.DISCONNECTED
            self._connect_task = None
            return False

    async def disconnect(self) -> None:
        if not self.connected:
            return

        self.connection_status = ConnectionStatus.DISCONNECTING

        if self._disconnect_task is not None:
            raise ConnectionError("Disconnect is already started.")

        async def disconnect_coro():
            if self._connect_task is not None:
                self._connect_task.cancel()
                await asyncio.sleep(2)
                self._connect_task = None

            await asyncio.sleep(1)

        self._disconnect_task = asyncio.create_task(disconnect_coro())
        await self._disconnect_task

        self.connection_status = ConnectionStatus.DISCONNECTED
        self._disconnect_task = None

    def cancel(self) -> None:
        logger.info("Cancelling connection requested.")
        self.connection_status = ConnectionStatus.CANCELLING
        if self._connect_task is not None:
            self._connect_task.cancel()
            self._connect_task = None
            self.connection_status = ConnectionStatus.DISCONNECTED

        if self._disconnect_task is not None:
            self._disconnect_task.cancel()
            self._disconnect_task = None
            self.connection_status = ConnectionStatus.CONNECTED
