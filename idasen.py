import os
from subprocess import Popen
from typing import Callable
import wx.adv
import yaml

IDASEN_CONFIG_PATH = "~/.config/idasen/idasen.yaml"
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
        set_idasen_position(position_name)

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


class App(wx.App):
    def OnInit(self):
        frame = wx.Frame(None)
        self.SetTopWindow(frame)
        TaskBarIcon(frame)
        return True


def main():
    app = App(False)
    app.MainLoop()


if __name__ == "__main__":
    main()
