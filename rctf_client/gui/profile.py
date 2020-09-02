import urwid
from datetime import datetime
import pyperclip

from .components import Alert, Dialog, TextBox, RadioBox
from ..util import ordinal_suffix

class ProfilePage(urwid.Columns):
  def __init__(self, client, config):
    self.client = client
    self.config = config
    self.profile = self.client.private_profile()
    super().__init__([])
    self.reload()
    urwid.register_signal(ProfilePage, ["dialog_open", "dialog_close"])

  def msg(self, *args, msg, title, **kwargs):
    dialog = Alert(str(msg), on_ok=self.dialog_close, title=title)
    urwid.emit_signal(self, "dialog_open", dialog)

  def edit_info(self, button, user_data):
    try:
      email = user_data.email.get_value()
      if email != self.profile["email"]:
        self.client.update_email(email)
      name = user_data.name.get_value()
      division = user_data.division.get_value()
      if name != self.profile["name"] or division != self.profile["division"]:
        self.client.update_account(name=name, division=division)
    except Exception as e:
      self.msg(msg=e, title="Error")
    finally:
      self.reload()

  def dialog_close(self, *args, **kwargs):
    urwid.emit_signal(self, "dialog_close")

  def reload(self):
    self.profile = self.client.private_profile()
    self.token = ProfileToken(self.profile["teamToken"])
    self.info = ProfileInfo(self.profile, self.client.config["divisions"], self.edit_info)
    left_widgets = [
      self.token,
      self.info,
    ]
    if self.client.config["userMembers"]:
      self.members = TeamMembers(self.client, on_msg=self.msg, reload=self.reload)
      left_widgets.append(self.members)
    self.left_column = urwid.ListBox(left_widgets)
    self.solves = ProfileSolves(self.profile)
    self.solves.set_title("Solves (S)")
    self.right_column = urwid.Pile([
      ("pack", ProfileSummary(self.profile, self.client.config["divisions"])),
      self.solves,
    ])
    self.contents = [
      (self.left_column, self.options()),
      (self.right_column, self.options()),
    ]
    self.set_focus(0)

  def keypress(self, size, key):
    if super().keypress(size, key) is None:
      return
    if key == "t":
      self.token.copy()
    elif key == "i":
      self.set_focus(0)
      self.left_column.set_focus(1)
    elif key == "m":
      self.set_focus(0)
      self.left_column.set_focus(2)
    elif key == "s":
      self.set_focus(1)
    return key

class ProfileSummary(urwid.LineBox):
  def __init__(self, profile, divisions):
    points = f"{profile['score']} total points" if profile["score"] > 0 else "No points earned"
    division_place = f"{ordinal_suffix(profile['divisionPlace'])} place in the {divisions[profile['division']]} division" if profile["divisionPlace"] else "Unranked"
    global_place = f"{ordinal_suffix(profile['globalPlace'])} place across all teams" if profile["globalPlace"] else "Unranked"
    division = f"{divisions[profile['division']]} division"
    widgets = [
      urwid.Text(points),
      urwid.Text(division_place),
      urwid.Text(global_place),
      urwid.Text(division),
    ]
    super().__init__(urwid.Pile(widgets), title=profile["name"], title_align="left")

class ProfileSolves(urwid.LineBox):
  def __init__(self, data):
    header = urwid.Pile([
      urwid.Columns([
        urwid.Text("Category"),
        urwid.Text("Challenge"),
        urwid.Text("Solve time"),
        urwid.Text("Points"),
      ], dividechars=1),
      urwid.Divider("─"),
    ])
    rows = [ProfileSolvesRow(solve) for solve in data["solves"]]
    solves = urwid.ListBox(rows)
    super().__init__(urwid.Frame(solves, header=header), title="Solves", title_align="left")

class ProfileSolvesRow(urwid.WidgetWrap):
  def __init__(self, solve):
    ts = datetime.utcfromtimestamp(solve["createdAt"] / 1000.0)
    self.contents = [
      urwid.Text(solve["category"]),
      urwid.Text(solve["name"]),
      urwid.Text(str(ts)),
      urwid.Text(str(solve["points"])),
    ]
    super().__init__(urwid.Columns(self.contents, dividechars=1))

class ProfileToken(urwid.LineBox):
  def __init__(self, token):
    self.token = token
    super().__init__(urwid.Pile([
      urwid.Text("Use this token to log in"),
      urwid.Button("Copy to Clipboard (T)", on_press=self.copy)
    ]), title="Login Token", title_align="left")

  def copy(self, button=None):
    urwid.emit_signal(self, "dialog_open")
    pyperclip.copy(self.token)

class ProfileInfo(urwid.LineBox):
  def __init__(self, profile, divisions, on_edit_profile=None):
    options = {k: divisions[k] for k in profile["allowedDivisions"]}
    self.name = TextBox(profile["name"], "Team Name")
    self.email = TextBox(profile["email"], "Email")
    self.division = RadioBox(options, profile["division"], "Division")
    super().__init__(urwid.Pile([
      self.name,
      self.email,
      self.division,
      urwid.Button("Save", on_press=on_edit_profile, user_data=self),
    ]), title="Team Information (I)", title_align="left")

class TeamMembers(urwid.LineBox):
  def __init__(self, client, on_msg=None, reload=None):
    self.client = client
    self.on_msg = on_msg
    self.reload = reload
    members = self.client.get_members()
    self.email = TextBox("", "Add Member Email")
    urwid.connect_signal(self.email, "activate", self.add_member)
    if len(members) == 0:
      self.member_list = [urwid.Text("no members")]
    else:
      self.member_list = [TeamMemberRow(member, on_delete=self.remove_member) for member in members]
    super().__init__(urwid.Pile([
      self.email,
      urwid.Divider("─"),
      *self.member_list,
    ]), title="Team Members (M)", title_align="left")

  def add_member(self, *args, **kwargs):
    try:
      self.client.add_member(self.email.get_value())
      if self.reload:
        self.reload()
    except Exception as e:
      if self.on_msg:
        self.on_msg(msg=e, title="Error")

  def remove_member(self, button, user_data):
    try:
      self.client.remove_member(user_data)
      if self.reload:
        self.reload()
    except Exception as e:
      if self.on_msg:
        self.on_msg(msg=e, title="Error")

class TeamMemberRow(urwid.Columns):
  def __init__(self, member, on_delete=None):
    super().__init__([
      urwid.Text(member["email"]),
      (10, urwid.Button("Remove", on_press=on_delete, user_data=member["id"])),
    ], dividechars=1)
