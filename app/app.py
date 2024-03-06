from flask import Flask

from load_models import MODEL, VOCODER, DENOISER, G2P

from urls import interface


app = Flask(__name__)
app.register_blueprint(interface)


if __name__ == "__main__":
    app.run(debug=True)
