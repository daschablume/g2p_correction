from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from app.config import Config
from app.load_models import G2P, MATCHA_MODEL, VOCODER, DENOISER
from app.urls import interface


app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
migrate = Migrate(app, db)

app.register_blueprint(interface)

# for sqlalchemy to work with flask
app.app_context().push()

from app import models


if __name__ == "__main__":
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', 5000))
    app.run(debug=False, host=host, port=port)
