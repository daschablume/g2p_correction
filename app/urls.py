from flask import Blueprint

import views

interface = Blueprint('interface', __name__)

interface.add_url_rule(
    '/', view_func=views.text_to_audio,
    methods=['GET', 'POST']
)
