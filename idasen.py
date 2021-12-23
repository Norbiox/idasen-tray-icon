import argparse
import logging
import os
import time
from subprocess import Popen
from threading import Thread
from typing import Callable

import wx.adv
import wx.lib.newevent
import yaml

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch.setFormatter(formatter)
log.addHandler(ch)


IDASEN_CONFIG_PATH = "~/.config/idasen/idasen.yaml"
POSITIONS_TIMES = {
    "stand": 1,
    "sit": 1,
}
TRAY_ICON = "icon.png"
TRAY_TOOLTIP = "Idasen"


def create_menu_item(menu: wx.Menu, label: str, func: Callable):
    item = wx.MenuItem(menu, -1, label)
    menu.Bind(wx.EVT_MENU, func, id=item.GetId())
    menu.Append(item)
    return item


def read_positions_from_idasen_config_file() -> dict[str, int]:
    config_path = os.path.expanduser(IDASEN_CONFIG_PATH)
    with open(config_path, "r") as file:
        config = yaml.safe_load(file)
    return config["positions"]


def set_idasen_position(position: str):
    Popen(
        ["idasen", position],
        stdin=None,
        stdout=None,
        stderr=None,
    )


EVT_POSITION_CHANGE_ID = wx.NewIdRef()

PositionChangeEvent, EVT_POSITION_CHANGE = wx.lib.newevent.NewCommandEvent()
PositionTimeoutEvent, EVT_POSITION_TIMEOUT = wx.lib.newevent.NewEvent()


class TimeCounter(Thread):
    """This thread counts time (in minutes) and posts event on timeout."""

    def __init__(self, notify_window, timeout_event):
        Thread.__init__(self)
        self._notify_window = notify_window
        self._timeout_event = timeout_event
        self._want_abort = False

    def start(self, time: int):
        self._sleep_time = time * 60
        Thread.start(self)

    def run(self):
        log.debug("Timer started!")
        time.sleep(self._sleep_time)
        log.debug("Timeout!")
        if self._want_abort:
            return
        log.debug(f"Posting {self._timeout_event.__class__.__name__}...")
        wx.PostEvent(self._notify_window, self._timeout_event)

    def abort(self):
        log.debug("Counting aborted...")
        self._want_abort = True


class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame):
        self.frame = frame
        super(TaskBarIcon, self).__init__()
        self.set_icon(TRAY_ICON)
        self.Bind(wx.adv.EVT_TASKBAR_LEFT_DOWN, self.on_left_down)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        self.add_positions_to_menu(menu)
        menu.AppendSeparator()
        create_menu_item(menu, "Exit", self.on_exit)
        return menu

    def set_icon(self, path):
        icon = wx.Icon(wx.Bitmap(path))
        self.SetIcon(icon, TRAY_TOOLTIP)

    def on_left_down(self, event):
        print("Tray icon was left-clicked.")

    def on_hello(self, event):
        print("Hello, world!")

    def on_exit(self, event):
        wx.CallAfter(self.Destroy)
        self.frame.Close()

    def on_position(self, event, position_name):
        if position_name == self.frame.current_position:
            return
        new_event = PositionChangeEvent(EVT_POSITION_CHANGE_ID, position=position_name)
        wx.PostEvent(self.frame, new_event)

    def add_positions_to_menu(self, menu: wx.Menu):
        positions = read_positions_from_idasen_config_file()
        for position_name, height in positions.items():
            menu.Append
            create_menu_item(
                menu,
                f"{position_name}  ({height}m)",
                # lambda position_name: set_idasen_position(position_name),
                lambda event, position_name=position_name: self.on_position(event, position_name),
            )


class MainFrame(wx.Frame):
    def __init__(self, parent, id, enable_position_change_nagging=True):
        wx.Frame.__init__(self, parent, id, "Idasen")
        self.__position_change_nagging_enabled = enable_position_change_nagging
        self.__position_change_counter = None
        self.__position = None

        self.Bind(EVT_POSITION_CHANGE, self._change_position)
        self.Bind(EVT_POSITION_TIMEOUT, self._toggle_position)

    @property
    def current_position(self):
        return self.__position

    def _change_position(self, event):
        """Sets position and sets up time counter"""
        if event.position not in read_positions_from_idasen_config_file():
            log.error(f"Position {event.position} is not valid position name")
            return
        log.debug(f"Changing position to {event.position}...")
        self.__position = event.position
        set_idasen_position(event.position)
        if self.__position_change_nagging_enabled:
            self._start_position_change_counter(event.position)

    def _start_position_change_counter(self, position_name):
        """Creates new time counter and sets it up to proper time."""
        max_time_at_position = POSITIONS_TIMES.get(position_name, None)
        if not max_time_at_position:
            return
        if self.__position_change_counter:
            self.__position_change_counter.abort()
        log.debug(f"Setting counter to {max_time_at_position} minutes...")
        self.__position_change_counter = TimeCounter(self, PositionTimeoutEvent())
        self.__position_change_counter.start(max_time_at_position)

    def _toggle_position(self, event):
        """Toggles position from sit to stand and vice-versa"""
        log.debug("Position timeout, toggling position...")
        next_position = "sit" if self.current_position == "stand" else "stand"
        new_event = PositionChangeEvent(EVT_POSITION_CHANGE_ID, position=next_position)
        wx.PostEvent(self, new_event)


class App(wx.App):
    def OnInit(self):
        self.frame = MainFrame(None, -1)
        self.SetTopWindow(self.frame)
        TaskBarIcon(self.frame)
        return True


def main():
    app = App(False)
    app.MainLoop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Idasen tray icon.")
    parser.add_argument("-l", "--log", action="store_true", help="Log to file")
    args = parser.parse_args()

    if args.log:
        ch = logging.FileHandler("idasen.log")
        ch.setLevel(logging.DEBUG)
        log.addHandler(ch)

    log.info("Starting...")
    main()
    log.info("Stopping...")
