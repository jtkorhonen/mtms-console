#!/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from signal import signal, SIGINT
import sys
import os
import datetime
import logging
import logging.config
import asyncio
import urwid
import urwid.curses_display
from variable import Variable, StateVariable, AutomaticStateVariable  # noqa: F401
from model import create_mtms_model
from ui import create_mtms_ui

VERSION = "0.0.1"


def setup_logging():
    """Sets up a logger instance.
    """
    logpath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../logs")
    if not os.path.exists(logpath):
        print(
            f"Error. Log directory ({logpath}) does not exist. Please create manually first.")
        sys.exit(1)

    logfilename = f"{os.path.basename(__file__)}.log.{datetime.datetime.now().replace(microsecond=0).isoformat()}"
    logfile = os.path.join(logpath, logfilename)

    logging.basicConfig(
        filename=logfile,
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create a symlink to ".latest"
    latest_logfilename = f"{os.path.basename(__file__)}.log.latest"
    latest_logfile = os.path.join(logpath, latest_logfilename)
    if os.path.exists(latest_logfile):
        os.remove(latest_logfile)
    os.symlink(logfile, latest_logfile)


setup_logging()
logger = logging.getLogger(__name__)
logger.info(f"Log started on {datetime.datetime.now().isoformat()}.")


def exit_handler(signal_received, frame):
    logger.info("SIGINT or Ctrl+C detected. Exiting.")
    raise urwid.ExitMainLoop()

### Run function ###############################################################


def run_ui():
    # Set up exit with Ctrl-Q
    async def exit_on_q(key):
        if key in ('ctrl q', ):
            logger.info("Received exit signal.")

            try:
                mtms_ui.freeze_ui()
                await mtms_model.connection.disconnect()
            except (NameError, AttributeError):
                pass

            raise urwid.ExitMainLoop()

    # Create model
    mtms_model = create_mtms_model()

    # Create CLI
    mtms_ui = create_mtms_ui(model=mtms_model, version=VERSION)

    # Start loop
    asyncio_loop = asyncio.get_event_loop()
    event_loop = urwid.AsyncioEventLoop(loop=asyncio_loop)
    loop = urwid.MainLoop(mtms_ui,
                          event_loop=event_loop,
                          screen=urwid.raw_display.Screen(),
                          unhandled_input=lambda key: asyncio.create_task(exit_on_q(key)))
    loop.run()


if __name__ == "__main__":
    logger.info("Starting main program.")
    signal(SIGINT, exit_handler)   # Attach an exit listener
    run_ui()
