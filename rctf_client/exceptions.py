class APIError(Exception):
  def __init__(self, kind, message):
    self.kind = kind
    self.message = message
    super().__init__(self.message)

  def __str__(self):
    return f"{self.kind}: {self.message}"
