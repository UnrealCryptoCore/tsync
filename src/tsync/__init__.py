import os
from flask import Flask
from dotenv import load_dotenv


def load_resource_links():
    """
    Loads links for page /resources
    Format: {link}={name}
    """

    try:
        lines = open("resourcelinks.txt").readlines()
        links = [line.split("=") for line in lines]
        links = [(link[0].strip(), link[1].strip()) for link in links]
        return links
    except FileNotFoundError:
        return []


def create_app():
    """
    creates the flask server
    """

    load_dotenv()

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET").encode("utf-8"),
        DATABASE="tsync.db",
        PEPPER=os.getenv("PEPPER").encode("utf-8"),
        URL=os.getenv("URL", "localhost"),
        RESOURCE_LINKS=load_resource_links(),
        UPLOAD_FOLDER="./data/",
    )

    from . import db
    db.init_app(app)

    from . import auth
    from . import tsync
    app.register_blueprint(auth.bp)
    app.register_blueprint(tsync.bp)

    app.add_url_rule('/', endpoint='index')

    return app
