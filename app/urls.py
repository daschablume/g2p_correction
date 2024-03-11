from flask import Blueprint

from app.views import text_to_audio_view, grapheme_log_view

interface = Blueprint('interface', __name__)

interface.add_url_rule(
    '/', view_func=text_to_audio_view,
    methods=['GET', 'POST']
)
interface.add_url_rule(
    '/grapheme-log/<int:grapheme_id>',
    view_func=grapheme_log_view,
    methods=['GET']
)
