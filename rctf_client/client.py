from requests import request
import urllib

from .exceptions import APIError

API_VERSION = "v1"

def _handle_response(resp, valid, message=False):
  if resp["kind"] in valid:
    if message:
      return resp["message"]
    return resp["data"]
  raise APIError(resp["kind"], resp["message"])

class RCTFClient:
  def __init__(self, url, token=None):
    if not urllib.parse.urlparse(url).scheme in ["http", "https"]:
      raise ValueError(f"Invalid URL: {url}")
    self.url = url
    self.token = token
    self.config = self._config()
    if self.token:
      self.private_profile()

  def _request(self, method, endpoint, **data):
    url = urllib.parse.urljoin(self.url, f"/api/{API_VERSION}{endpoint}")

    if data:
      data = {k: v for k, v in data.items() if v is not None}

    headers = {}
    if self.token:
      headers["Authorization"] = f"Bearer {self.token}"

    if method == "GET" and data:
      resp = request(
        method, url,
        headers=headers,
        params=data,
      )
    else:
      resp = request(
        method, url,
        headers=headers,
        json=data,
      )
    return resp.json()

  def _config(self):
    response = self._request("GET", "/integrations/client/config")
    return _handle_response(response, ["goodClientConfig"])

  def login(self, token):
    response = self._request("POST", "/auth/login",
      teamToken=token,
    )
    self.token = _handle_response(response, ["goodLogin"])["authToken"]

  def get_challenges(self):
    response = self._request("GET", "/challs")
    return _handle_response(response, ["goodChallenges"])

  def get_solves(self, chall, limit=10, offset=0):
    response = self._request("GET", f"/challs/{urllib.parse.quote(chall)}/solves",
      limit=limit,
      offset=offset,
    )
    return _handle_response(response, ["goodChallengeSolves"])

  def submit_flag(self, chall, flag):
    response = self._request("POST", f"/challs/{urllib.parse.quote(chall)}/submit",
      flag=flag,
    )
    return _handle_response(response, ["goodFlag"])

  def get_members(self):
    response = self._request("GET", "/users/me/members")
    return _handle_response(response, ["goodMemberData"])

  def add_member(self, email):
    response = self._request("POST", "/users/me/members",
      email=email
    )
    return _handle_response(response, ["goodMemberCreate"])

  def remove_member(self, member):
    response = self._request("DELETE", f"/users/me/members/{member}")
    return _handle_response(response, ["goodMemberDelete"])

  def private_profile(self):
    response = self._request("GET", "/users/me")
    return _handle_response(response, ["goodUserData"])

  def public_profile(self, uuid):
    response = self._request("GET", f"/users/{urllib.parse.quote(uuid)}")
    return _handle_response(response, ["goodUserData"])

  def update_account(self, name=None, division=None):
    response = self._request("PATCH", "/users/me",
      name=name,
      division=division,
    )
    return _handle_response(response, ["goodUserUpdate"])

  def update_email(self, email):
    response = self._request("PUT", "/users/me/auth/email",
      email=email,
    )
    return _handle_response(response, ["goodVerifyEmailSent", "goodEmailSet"], message=True)

  def delete_email(self):
    response = self._request("DELETE", "/users/me/auth/email")
    return _handle_response(response, ["goodEmailRemoved", "badEmailNoExists"], message=True)

  def get_scoreboard(self, division=None, limit=100, offset=0):
    response = self._request("GET", "/leaderboard/now",
      division=division,
      limit=limit,
      offset=offset,
    )
    return _handle_response(response, ["goodLeaderboard"])

  def get_graph(self, division=None, limit=10):
    response = self._request("GET", "/leaderboard/graph",
      division=division,
      limit=limit,
    )
    return _handle_response(response, ["goodLeaderboard"])
