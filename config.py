import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "copilot-roadmap-dev-key-change-in-prod")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'roadmap.db')}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ROADMAP_RSS_URL = "https://www.microsoft.com/releasecommunications/api/v2/m365/rss"
    ROADMAP_FETCH_TIMEOUT = 30
