from flask import Blueprint

from app.views import text_to_audio_view

interface = Blueprint('interface', __name__)

interface.add_url_rule(
    '/', view_func=text_to_audio_view,
    methods=['GET', 'POST']
)
