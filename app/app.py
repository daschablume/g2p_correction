from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from .config import Config
from .load_models import MODEL, VOCODER, DENOISER, G2P
from .urls import interface


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

app.register_blueprint(interface)

from . import models


if __name__ == "__main__":
    app.run(debug=True)
