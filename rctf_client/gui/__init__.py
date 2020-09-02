import pathlib
import urwid

from .header import HeaderWidget
from .scoreboard import ScoreboardPage
from .profile import ProfilePage
from .challenges import ChallengesPage

keymap = {
  "k": "cursor up",
  "j": "cursor down",
  "h": "cursor left",
  "l": "cursor right",
  "ctrl u": "cursor page up",
  "ctrl d": "cursor page down",
}
for key, command in keymap.items():
  urwid.command_map[key] = command

class GUI:
  palette = [
    ("header", "black", "white"),
    ("body", "white", "black"),
    ("highlight", "black", "light red"),
    ("edit", "light gray", "light blue"),
  ]
  def __init__(self, client, config, ctf_root):
    self.client = client
    self.config = config
    self.ctf_root = ctf_root
    self.tabs = [
      ("Scoreboard", ScoreboardPage(self.client, self.config)),
      ("Profile", ProfilePage(self.client, self.config)),
      ("Challenges", ChallengesPage(self.client, self.config, self.ctf_root)),
    ]
    for tab in self.tabs:
      urwid.connect_signal(tab[1], "dialog_open", self.dialog_open)
      urwid.connect_signal(tab[1], "dialog_close", self.dialog_close)
    self.tab_keys = [str(x) for x in range(1, len(self.tabs)+1)]
    self.dialog_state = False
    self.header = urwid.AttrWrap(HeaderWidget(client, self.tabs), "header")
    self.view = urwid.Frame(
      self.tabs[0][1],
      header=self.header,
    )
    self.select_tab(self.config.get("selected_tab", 0))

  def select_tab(self, tab):
    self.header.select_tab(tab)
    self.view.body = self.tabs[tab][1]
    self.config["selected_tab"] = tab

  def unhandled_input(self, k):
    if k == "q":
      raise urwid.ExitMainLoop()
    if self.dialog_state:
      return
    if k in self.tab_keys:
      self.select_tab(int(k)-1)
    if k == "r":
      if hasattr(self.view.body, "reload"):
        self.view.body.reload()

  def dialog_open(self, popup):
    self.loop.widget = urwid.Overlay(
      popup, self.loop.widget,
      "center", ("relative", 30), "middle", "pack",
    )
    self.dialog_state = True

  def dialog_close(self):
    self.loop.widget = self.view
    self.dialog_state = False

  def main(self):
    self.loop = urwid.MainLoop(self.view, self.palette,
      handle_mouse=False,
      unhandled_input=self.unhandled_input
    )
    try:
      self.loop.run()
    except KeyboardInterrupt:
      return
    except Exception as e:
      raise e from None