import click
import json
import yaml

from ..util import download_challenge

output_functions = {
  "json": json.dumps,
  "yaml": yaml.dump,
}

def pretty(challenge):
  width, _ = click.get_terminal_size()
  header = f"─ {challenge['category']}/{challenge['name']} (ID: {challenge['id']}) ".ljust(width, "─")
  files = "".join(f"\n  - {f['name']} ({f['url']})" for f in challenge["files"])
  return f"""{header}
({challenge['solves']} solve{'s' if challenge['solves'] != 1 else ""} / {challenge['points']} point{'s' if challenge['points'] != 1 else ""})
Author: {challenge['author']}

{challenge['description']}

{"Files: " + files if challenge["files"] else "(none)"}
"""

@click.command("list")
@click.pass_context
@click.option("-s", "--solved", is_flag=True, default=False, show_default=True, help="show solved challenges")
@click.option("-i", "--include", metavar="<category>", default=[], show_default="include all categories", help="categories to include, can specify multiple times", multiple=True)
@click.option("-f", "--format", type=click.Choice(["pretty", "json", "yaml"]), default="pretty", show_default=True, help="output format")
def list_challenges(ctx, solved, include, format):
  """List challenges"""
  client = ctx.obj["client"]
  challenges = sorted(client.get_challenges(), key=lambda x: -x.get("sortWeight", 0))
  if len(include) > 0:
    challenges = [challenge for challenge in challenges if challenge["category"] in include]
  if not solved:
    solves = set(solve["id"] for solve in client.private_profile()["solves"])
    challenges = [challenge for challenge in challenges if challenge["id"] not in solves]

  if len(challenges) == 0:
    click.echo("No challenges!", err=True)
    return

  if format == "pretty":
    click.echo_via_pager("\n".join(pretty(challenge) for challenge in challenges))
  else:
    click.echo(output_functions[format](challenges))

@click.command()
@click.pass_context
@click.argument("id")
@click.option("-f", "--format", type=click.Choice(["pretty", "json", "yaml"]), default="pretty", show_default=True, help="output format")
def show(ctx, id, format):
  """Show challenge by ID"""
  client = ctx.obj["client"]
  challenges = client.get_challenges()
  challenge = next(filter(lambda challenge: challenge["id"] == id, challenges), None)
  if challenge:
    if format == "pretty":
      click.echo_via_pager(pretty(challenge))
    else:
      click.echo_(output_functions[format](challenge))
  else:
    click.echo("Could not find challenge!", err=True)

@click.command()
@click.pass_context
@click.option("-i", "--include", metavar="<challenge>", default=[], show_default="include all challenges", help="challenges (by ID) to include, can specify multiple times", multiple=True)
def download(ctx, include):
  """Download challenge files and information"""
  client = ctx.obj["client"]
  config = ctx.obj["config"]
  ctf_root = ctx.obj["ctf_root"]
  challenges = client.get_challenges()
  if len(include) > 0:
    challenges = [challenge for challenge in challenges if challenge["id"] in include]
  if len(challenges) == 0:
    click.echo("Could not find challenge!", err=True)
    return
  with click.progressbar(challenges, label="Saving challenges") as bar:
    for challenge in bar:
      download_challenge(ctf_root, config, challenge)

@click.command()
@click.pass_context
@click.argument("challenge")
@click.argument("flag")
def submit(ctx, challenge, flag):
  """Submit a flag

  CHALLENGE is the challenge ID, and FLAG is the flag
  """
  client = ctx.obj["client"]
  try:
    client.submit_flag(challenge, flag)
    click.echo("Flag submitted!")
  except Exception as e:
    click.echo(e, err=True)
    return