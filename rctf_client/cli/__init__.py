import traceback

import click
import json
import pathlib

from ..client import RCTFClient
from ..exceptions import APIError
from ..gui import GUI
from ..util import find_file, cwd_from_file

@click.group()
@click.pass_context
def rctf(ctx):
  """CLI and TUI client for rCTF"""
  try:
    config_path = find_file(".rctf.json")
    ctf_root = config_path.parent
    with open(config_path) as f:
      config = json.load(f)
    client = RCTFClient(config["url"], config["token"])
  except (FileNotFoundError, KeyError):
    try:
      url = click.prompt("rCTF URL")
      token = click.prompt("Login Token")
      client = RCTFClient(url)
      client.login(token)
      config = {
        "url": client.url,
        "token": client.token,
      }
      ctf_root = pathlib.Path.cwd().resolve()
    except Exception as e:                              # TODO: do this better
      click.echo(e, err=True)
      return
  except Exception as e:
    click.echo(e, err=True)
    return
  ctx.obj = {
    "client": client,
    "config": config,
    "ctf_root": ctf_root,
  }

@rctf.resultcallback()
@click.pass_context
def save_config(ctx, result, **kwargs):
  with open(ctx.obj["ctf_root"] / ".rctf.json", "w") as f:
    json.dump(ctx.obj["config"], f, indent=2)

@rctf.command()
def init():
  """Perform first-time setup and do nothing"""
  pass

@rctf.command()
@click.pass_context
def gui(ctx):
  """Start Terminal UI"""
  client, config, ctf_root = ctx.obj["client"], ctx.obj["config"], ctx.obj["ctf_root"]
  try:
    GUI(client, config, ctf_root).main()
    click.clear()
  except:
    click.echo(traceback.format_exc(), err=True)
    return

from .challenges import list_challenges, show, download, submit

@rctf.group()
def challenges():
  """Manage challenges"""
  pass

challenges.add_command(list_challenges)
challenges.add_command(show)
challenges.add_command(download)
challenges.add_command(submit)

@rctf.command("submit")
@click.pass_context
@click.argument("flag")
def challenge_submit(ctx, flag):
  """Submit a challenge from its directory"""
  config = ctx.obj["config"]
  relative_path = str(cwd_from_file(ctx.obj["ctf_root"]))
  if "challenge_dirs" in config and relative_path in config["challenge_dirs"]:
    ctx.invoke(submit, challenge=config["challenge_dirs"][relative_path], flag=flag)
  else:
    click.echo("Could not find challenge!", err=True)
    return
