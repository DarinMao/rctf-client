import urwid
from urwid.command_map import ACTIVATE

class Dialog(urwid.LineBox):
  def __init__(self, widget, *args, **kwargs):
    super().__init__(widget, *args, **kwargs)

class Alert(Dialog):
  def __init__(self, text, *args, on_ok=None, **kwargs):
    self.on_ok = on_ok
    super().__init__(urwid.Pile([
      urwid.Text(text),
      urwid.Button("Ok", on_press=on_ok, user_data=self),
    ]), *args, **kwargs)

class TextBox(urwid.LineBox):
  def __init__(self, value="", label=""):
    self.value = value
    self.edit = urwid.Edit(edit_text=value)
    super().__init__(urwid.AttrWrap(self.edit, "body", "highlight"), title=label, title_align="left")
    urwid.register_signal(TextBox, ["activate"])

  def get_value(self):
    return self.edit.get_edit_text()

  def keypress(self, size, key):
    if urwid.command_map[key] == ACTIVATE:
      urwid.emit_signal(self, "activate")
    if self.edit.keypress(size, key) is None:
      return
    return super().keypress(size, key)

class RadioBox(urwid.LineBox):
  def __init__(self, options, selected="", label=""):
    self.group = []
    self.value = selected
    for k, v in options.items():
      urwid.RadioButton(self.group, v,
        state=(selected == k),
        on_state_change=self.set_value,
        user_data=k,
      )
    super().__init__(urwid.Pile(self.group), title=label, title_align="left")

  def set_value(self, button=None, state=None, user_data=None):
    if state:
      self.value = user_data

  def get_value(self):
    return self.value

class CheckBox(urwid.LineBox):
  def __init__(self, options, selected=[], label=""):
    self.value = set(selected)
    boxes = []
    for k, v in options.items():
      boxes.append(urwid.CheckBox(v,
        state=(k in selected),
        on_state_change=self.set_value,
        user_data=k,
      ))
    super().__init__(urwid.Pile(boxes), title=label, title_align="left")

  def set_value(self, button=None, state=None, user_data=None):
    if state:
      self.value.add(user_data)
    else:
      self.value.remove(user_data)

  def get_value(self):
    return self.value
