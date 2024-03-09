from .app import db
from .models import Grapheme, GraphemeLog


def add_graphemes_and_log(grapheme2phoneme: dict[str, str]):
    # it would probably be better to split add grapheme and add log into two functions
    # but it's more cumbersome to do so
    graphemes = (
        db.session.query(
            Grapheme.id, Grapheme.grapheme, Grapheme.phoneme)
        .filter(Grapheme.grapheme.in_(grapheme2phoneme.keys()))
        .all()
    )

    grapheme2id_phoneme = {g.grapheme: (g.id, g.phoneme) for g in graphemes}

    for grapheme, phoneme in grapheme2phoneme.items():
        # update grapheme if it already exists
        if grapheme in grapheme2id_phoneme:
            grapheme_id, from_phoneme = grapheme2id_phoneme[grapheme]
            (Grapheme.query
             .filter(Grapheme.id == grapheme_id)
             .update
                ({Grapheme.phoneme: phoneme}, synchronize_session=False))
            
            grapheme_log = _create_grapheme_log(grapheme_id, grapheme, phoneme, from_phoneme)

        else:
            grapheme = Grapheme(grapheme=grapheme, phoneme=phoneme)
            db.session.add(grapheme)
            db.session.flush()
            grapheme_log = _create_grapheme_log(grapheme.id, grapheme.grapheme, grapheme.phoneme)

        db.session.add(grapheme_log)


def fetch_grapheme2phoneme(graphemes: list[str]):
    grapheme2phoneme = dict(
        db.session.query(
            Grapheme.grapheme, Grapheme.phoneme)
        .filter(Grapheme.grapheme.in_(graphemes))
    )
    return grapheme2phoneme


def _create_grapheme_log(grapheme_id, grapheme_name, to_phoneme, from_phoneme=None):
    '''
    Create a grapheme log.
    '''
    grapheme_log = GraphemeLog(
        grapheme_id=grapheme_id,
        grapheme_name=grapheme_name,
        from_phoneme=from_phoneme,
        to_phoneme=to_phoneme
    )
    grapheme_log
    
    return grapheme_log


if __name__ == "__main__":
    add_graphemes_and_log({'is': 'ˈɪs', 'in': 'ˈɪn', 'the': 'ðə', 'sky': 'ski'})
