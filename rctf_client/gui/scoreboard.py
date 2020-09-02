import urwid
from urwid.command_map import (CURSOR_LEFT, CURSOR_RIGHT, ACTIVATE)

from .components import Dialog, RadioBox
from .profile import ProfileSummary, ProfileSolves

class ScoreboardPage(urwid.Columns):
  def __init__(self, client, config):
    self.client = client
    self.config = config
    self.division = self.config.get("scoreboard_division", None)
    super().__init__([])
    self.reload()
    urwid.register_signal(ScoreboardPage, ["dialog_open", "dialog_close"])

  def keypress(self, size, key):
    if key == "f":
      dialog = FilterDialog(self.client.config["divisions"],
        selected=self.division,
        on_save=self.save_division,
        on_cancel=self.dialog_close,
      )
      urwid.emit_signal(self, "dialog_open", dialog)
      return
    return super().keypress(size, key)

  def show_team(self, id):
    box = (PublicProfile(self.client, id, self.hide_team), self.options())
    self.contents = [self.contents[0], box]
    self.set_focus(1)

  def hide_team(self, widget):
    self.contents = [self.contents[0]]

  def save_division(self, button, user_data):
    self.dialog_close()
    division = user_data.division.get_value()
    if division == "":
      division = None
    self.config["scoreboard_division"] = division
    self.division = division
    self.reload()

  def dialog_close(self, *args, **kwargs):
    urwid.emit_signal(self, "dialog_close")

  def reload(self):
    self.contents = [(Scoreboard(self.client, self.division, self.show_team), self.options())]

class FilterDialog(Dialog):
  def __init__(self, divisions, selected=None, on_save=None, on_cancel=None):
    self.on_save = on_save
    self.on_cancel = on_cancel
    if selected is None:
      selected = ""
    group = []
    self.division = RadioBox({"": "All Divisions", **divisions}, selected, label="Division")
    buttons = urwid.Columns([
      urwid.Button("Save (S)", on_press=on_save, user_data=self),
      urwid.Button("Cancel (C)", on_press=on_cancel, user_data=self)
    ], dividechars=1)
    super().__init__(urwid.Pile([self.division, buttons]), title="Filter", title_align="left")

  def keypress(self, size, key):
    if self.on_save and key == "s":
      self.on_save(button=None, user_data=self)
    elif self.on_cancel and key == "c":
      self.on_cancel(button=None, user_data=self)
    else:
      return super().keypress(size, key)

class Scoreboard(urwid.LineBox):
  def __init__(self, client, division=None, on_select=None):
    self.division = division
    self.on_select = on_select
    data = client.get_scoreboard(division=self.division)
    if len(data["leaderboard"]) == 0:
      content = urwid.ListBox([urwid.Text("No teams")])
    else:
      header = urwid.Pile([
        urwid.Columns([
          (len(str(data["total"]))+1, urwid.Text("#")),
          urwid.Text("Team"),
          (max(7, len(str(data["leaderboard"][0]["score"]))+1), urwid.Text("Points")),
        ], dividechars=1),
        urwid.Divider("─"),
      ])
      content = urwid.Frame(urwid.ListBox(ScoreboardWalker(client, data, self.division, self._on_select)), header=header)
    title = "All Divisions" if self.division is None else f"{client.config['divisions'][self.division]} Division"
    title += " (F)"
    super().__init__(content, title=title, title_align="left")

  def _on_select(self, id):
    if self.on_select:
      self.on_select(id)

  def keypress(self, size, key):
    return super().keypress(size, key)

class ScoreboardWalker(urwid.ListWalker):
  def __init__(self, client, data, division, on_select=None):
    self.client = client
    self.on_select = on_select
    self.leaderboard, self.total = data["leaderboard"], data["total"]
    self.focus = 0
    self.division = division

  def __getitem__(self, key):
    if key >= len(self.leaderboard):
      data = self.client.get_scoreboard(
        division=self.division,
        offset=len(self.leaderboard)
      )
      self.leaderboard.extend(data["leaderboard"])

    return ScoreboardRow(self.leaderboard, self.total, key, self._on_select)

  def _on_select(self, row):
    if self.on_select:
      self.on_select(row.id)

  def next_position(self, position):
    if position+1 >= self.total:
      raise IndexError("Team index out of range")
    return position+1

  def prev_position(self, position):
    if position <= 0:
      raise IndexError("Team index out of range")
    return position-1

  def get_focus(self):
    return self[self.focus], self.focus

  def set_focus(self, focus):
    self.focus = focus
    self._modified()

class ScoreboardRow(urwid.WidgetWrap):
  def __init__(self, leaderboard, total, key, on_select=None):
    self.contents = [
      (len(str(total))+1, urwid.Text(str(key+1))),
      urwid.Text(leaderboard[key]["name"]),
      (len(str(leaderboard[0]["score"]))+1, urwid.Text(str(leaderboard[key]["score"]))),
    ]
    self.id = leaderboard[key]["id"]
    self.on_select = on_select
    self._columns = urwid.Columns(self.contents, dividechars=1)
    self._focusable_columns = urwid.AttrMap(self._columns, "", "highlight")
    super().__init__(self._focusable_columns)

  def selectable(self):
    return True

  def keypress(self, size, key):
    if self.on_select and urwid.command_map[key] in (CURSOR_RIGHT, ACTIVATE):
      self.on_select(self)
    return key

class PublicProfile(urwid.Pile):
  def __init__(self, client, id, on_leave=None):
    self.on_leave = on_leave
    data = client.public_profile(id)
    widgets = [
      ("pack", ProfileSummary(data, client.config["divisions"])),
      ProfileSolves(data),
    ]
    super().__init__(widgets, focus_item=1)

  def selectable(self):
    return True

  def keypress(self, size, key):
    if self.on_leave and urwid.command_map[key] == CURSOR_LEFT:
      self.on_leave(self)
      return
    return super().keypress(size, key)
