import urwid

class HeaderWidget(urwid.Padding):
  def __init__(self, client, tabs):
    self.client = client
    self.tabs = tabs
    self.selected_tab = 1
    self.text = urwid.Text(self.make_text())
    urwid.Padding.__init__(self, self.text, left=2, right=2)

  def make_text(self):
    text = [self.client.config["ctfName"]]
    for k, tab in enumerate(self.tabs):
      text += [" "*2]
      label = f"{tab[0]} ({k+1})"
      if k == self.selected_tab:
        text += [("highlight", label)]
      else:
        text += [label]

    return text

  def select_tab(self, tab):
    if tab < 0 or tab >= len(self.tabs):
      raise IndexError("Tab index out of range")
    self.selected_tab = tab
    self.text.set_text(self.make_text())
