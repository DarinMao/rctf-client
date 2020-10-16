import re
import pathlib
import requests
import shutil
import urllib

def ordinal_suffix(i):
  j = i % 10
  k = i % 100
  i = str(i)
  if j == 1 and k != 11:
    return i + "st"
  if j == 2 and k != 12:
    return i + "nd"
  if j == 3 and k != 13:
    return i + "rd"
  return i + "th"

def safe_name(name):
  name = re.sub("[^a-zA-Z0-9-_.]", "_", name)
  name = re.sub("^\.\.?$", "_", name)
  return name

def find_file(name, path=None):
  if path is None:
    path = pathlib.Path.cwd().resolve()
  dirs = [path] + list(path.parents)
  for directory in dirs:
    fp = directory / name
    if fp.is_file():
      return fp
  raise FileNotFoundError(f"No such file: '{name}'")

def cwd_from_file(path):
  return pathlib.Path.cwd().resolve().relative_to(path)

def make_challengedir(ctf_root, config, challenge):
  category = safe_name(challenge["category"])
  directory = safe_name(challenge["name"])
  challenge_root = ctf_root / category / directory
  challenge_root.mkdir(parents=True, exist_ok=True)
  config["challenge_dirs"] = {
    str(challenge_root.relative_to(ctf_root)): challenge["id"],
    **config.get("challenge_dirs", {})
  }
  return challenge_root

def download_challenge(ctf_root, config, challenge):
  challenge_root = make_challengedir(ctf_root, config, challenge)

  with open(challenge_root / "description.md", "w") as f:
    f.write(f"""# {challenge["category"]}/{challenge["name"]} (ID: {challenge["id"]})
## Author: {challenge["author"]}

{challenge["description"]}
""")

  if challenge["files"]:
    files_dir = challenge_root / "files"
    files_dir.mkdir(parents=True, exist_ok=True)
    for challenge_file in challenge["files"]:
      url = urllib.parse.urljoin(config["url"], challenge_file["url"])
      with requests.get(url, stream=True) as stream:
        with open(files_dir / safe_name(challenge_file["name"]), "wb") as fw:
          shutil.copyfileobj(stream.raw, fw)