from flask import Flask, redirect, render_template, request, session, g, flash, jsonify
from dotenv import load_dotenv
import sqlite3
import bcrypt
import os
import uuid
import sys
import secrets



def create_app():
    """
    creates the flask server
    """
    from . import test_parser

    load_dotenv()

    #from app import app
    #from . import app
    from .app import app

    return app


if __name__ == "__main__":
    app = create_app()
    if len(sys.argv) == 2 and sys.argv[1] == 'release':
        app.run(host='0.0.0.0', port=25566)
    else:
        app.run(debug=True)
