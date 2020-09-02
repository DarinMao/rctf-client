import os

import urwid
from urwid.command_map import (CURSOR_LEFT, CURSOR_RIGHT, ACTIVATE)

from .components import Alert, Dialog, CheckBox, TextBox

from ..util import download_challenge, make_challengedir

class ChallengesPage(urwid.Columns):
  def __init__(self, client, config, ctf_root):
    self.client = client
    self.config = config
    self.ctf_root = ctf_root
    if "challenges_showsolved" not in self.config:
      self.config["challenges_showsolved"] = False
    if "challenges_categories" not in self.config:
      self.config["challenges_categories"] = []
    super().__init__([])
    self.reload()
    urwid.register_signal(ChallengesPage, ["dialog_open", "dialog_close", "shell"])

  def keypress(self, size, key):
    if super().keypress(size, key) is None:
      return
    if key == "f":
      dialog = FilterDialog(
        {k: k for k in self.categories},
        self.config["challenges_categories"],
        self.config["challenges_showsolved"],
        on_save=self.save_filter,
        on_cancel=self.dialog_close,
      )
      urwid.emit_signal(self, "dialog_open", dialog)
    return key

  def msg(self, *args, msg, title="", **kwargs):
    dialog = Alert(str(msg), on_ok=self.dialog_close, title=title)
    urwid.emit_signal(self, "dialog_open", dialog)

  def dialog_close(self, *args, **kwargs):
    urwid.emit_signal(self, "dialog_close")

  def reload(self):
    challenges = self.client.get_challenges()
    self.categories = set(challenge["category"] for challenge in challenges)
    self.solves = set(solve["id"] for solve in self.client.private_profile()["solves"])
    self.challenge_tree = {}
    for challenge in challenges:
      if len(self.config["challenges_categories"]) > 0 and challenge["category"] not in self.config["challenges_categories"]:
        continue
      if not self.config["challenges_showsolved"] and challenge["id"] in self.solves:
        continue
      if challenge["category"] not in self.challenge_tree:
        self.challenge_tree[challenge["category"]] = []
      self.challenge_tree[challenge["category"]].append(challenge)
    categories_column = (
      Column({k: k for k in self.challenge_tree.keys()}, on_select=self.expand_category, title="Categories (F)", title_align="left"),
      self.options()
    )
    self.contents = [categories_column]

  def expand_category(self, category):
    self.category = category
    challenge_names = {k: (challenge["name"]+(" (Solved)" if challenge["id"] in self.solves else "")) for k, challenge in enumerate(self.challenge_tree[category])}
    challenges_column = (
      Column(challenge_names, on_select=self.expand_challenge, on_leave=self.close_category, title="Challenges", title_align="left"),
      self.options()
    )
    self.contents = self.contents[:1] + [challenges_column]
    self.set_focus(1)

  def close_category(self):
    self.category = None
    self.contents = self.contents[:1]
    self.set_focus(0)

  def expand_challenge(self, challenge):
    challenge = self.challenge_tree[self.category][challenge]
    self.challenge = challenge["id"]
    challenge_box = (Challenge(self.ctf_root, self.config, challenge, on_leave=self.close_challenge, on_submit=self.submit_flag, on_msg=self.msg), self.options(width_amount=4))
    self.contents = self.contents[:2] + [challenge_box]
    self.set_focus(2)

  def close_challenge(self):
    self.challenge = None
    self.contents = self.contents[:2]
    self.set_focus(1)

  def submit_flag(self, flag):
    try:
      self.client.submit_flag(self.challenge, flag.get_value())
      self.msg(msg="Flag submitted!")
      self.reload()
      self.expand_category(self.category)
    except Exception as e:
      self.msg(msg=e, title="Error")

  def save_filter(self, button, user_data):
    self.dialog_close()
    show_solved = len(user_data.show_solved.get_value()) > 0
    categories = sorted(list(user_data.categories.get_value()))
    if show_solved != self.config["challenges_showsolved"] or categories != self.config["challenges_categories"]:
      self.config["challenges_showsolved"] = show_solved
      self.config["challenges_categories"] = categories
      self.reload()

class FilterDialog(Dialog):
  def __init__(self, categories, selected_categories=[], show_solved=False, on_save=None, on_cancel=None):
    self.on_save = on_save
    self.on_cancel = on_cancel
    self.show_solved = CheckBox({"show": "Show Solved"}, (["show"] if show_solved else []))
    self.categories = CheckBox(categories, selected_categories, label="Categories")
    buttons = urwid.Columns([
      urwid.Button("Save (S)", on_press=on_save, user_data=self),
      urwid.Button("Cancel (C)", on_press=on_cancel, user_data=self),
    ], dividechars=1)
    super().__init__(urwid.Pile([self.show_solved, self.categories, buttons]), title="Filter", title_align="left")

  def keypress(self, size, key):
    if self.on_save and key == "s":
      self.on_save(button=None, user_data=self)
    elif self.on_cancel and key == "c":
      self.on_cancel(button=None, user_data=self)
    else:
      return super().keypress(size, key)

class Column(urwid.LineBox):
  def __init__(self, items, *args, on_select=None, on_leave=None, **kwargs):
    self.on_select = on_select
    self.on_leave = on_leave
    super().__init__(urwid.ListBox([
      ColumnRow(key, text, self._on_select) for key, text in items.items()
      ]), *args, **kwargs)

  def _on_select(self, row):
    if self.on_select:
      self.on_select(row.key)

  def keypress(self, size, key):
    if self.on_leave and urwid.command_map[key] == CURSOR_LEFT:
      self.on_leave()
    else:
      return super().keypress(size, key)

class ColumnRow(urwid.WidgetWrap):
  def __init__(self, key, text, on_select=None):
    self.key = key
    self.text = text
    self.on_select = on_select
    super().__init__(urwid.AttrMap(urwid.Text(text, wrap="clip"), "body", "highlight"))

  def selectable(self):
    return True

  def keypress(self, size, key):
    if self.on_select and urwid.command_map[key] in (CURSOR_RIGHT, ACTIVATE):
      self.on_select(self)
    return key

class Challenge(urwid.LineBox):
  def __init__(self, ctf_root, config, challenge, on_leave=None, on_submit=None, on_msg=None):
    self.ctf_root = ctf_root
    self.config = config
    self.challenge = challenge
    self.on_leave = on_leave
    self.on_msg = on_msg
    title = f"{challenge['category']}/{challenge['name']} ({challenge['solves']} solve{'s' if challenge['solves'] != 1 else ''} / {challenge['points']} point{'s' if challenge['points'] != 1 else ''})"
    files = [f"  - {f['name']} ({f['url']})" for f in challenge["files"]]
    if len(files) == 0:
      files = ["(none)"]
    files = [urwid.Text(text) for text in files]
    self.submit = TextBox(label="Submit (S)")
    urwid.connect_signal(self.submit, "activate", on_submit, user_args=[self.submit])
    self.list = urwid.ListBox([
      urwid.Text(f"Author: {challenge['author']}"),
      urwid.Divider("─"),
      urwid.Text(challenge["description"]),
      urwid.Divider("─"),
      urwid.Text("Files:"),
      *files,
      urwid.Divider("─"),
      urwid.Button("Download (D)", on_press=self.download),
      urwid.Divider(" "),
      self.submit,
    ])
    super().__init__(self.list, title=title, title_align="left")

  def selectable(self):
    return True

  def download(self, *args, **kwargs):
    try:
      download_challenge(self.ctf_root, self.config, self.challenge)
      if self.on_msg:
        self.on_msg(msg="Successfully Downloaded")
    except Exception as e:
      if self.on_msg:
        self.on_msg(msg=e, title="Error")

  def keypress(self, size, key):
    if super().keypress(size, key) is None:
      return
    if self.on_leave and urwid.command_map[key] == CURSOR_LEFT:
      self.on_leave()
    elif key == "d":
      self.download()
    elif key == "s":
      self.list.set_focus(9)
    else:
      return key