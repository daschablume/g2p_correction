from app import db
from app.models import Grapheme, GraphemeLog


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
            # don't save to log graphemes which were picked by accident
            # in the form
            current_phoneme = Grapheme.query.get(grapheme_id).phoneme
            if current_phoneme == phoneme:
                continue
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


def fetch_grapheme_logs(grapheme_id: int):
    return (
        db.session.query(
            GraphemeLog.grapheme_name,
            GraphemeLog.from_phoneme,
            GraphemeLog.to_phoneme,
            GraphemeLog.date_modified)
        .filter(GraphemeLog.grapheme_id == grapheme_id)
        .order_by(GraphemeLog.date_modified.desc())
        .all()
    )


def fetch_grapheme(grapheme_id: int):
    grapheme = Grapheme.query.get(grapheme_id)
    return grapheme.grapheme, grapheme.phoneme


def _create_grapheme_log(grapheme_id, grapheme_name, to_phoneme, from_phoneme=None):
    grapheme_log = GraphemeLog(
        grapheme_id=grapheme_id,
        grapheme_name=grapheme_name,
        from_phoneme=from_phoneme,
        to_phoneme=to_phoneme
    )
    grapheme_log
    
    return grapheme_log


def fetch_grapheme_ids_by_name(graphemes: list):
    return dict(
        db.session.query(
            Grapheme.grapheme, Grapheme.id, )
        .filter(Grapheme.grapheme.in_(graphemes))
    )


def filter_out_existing_words(word2phones: dict[str, list[str]]):
    existing_words = set(
        row.grapheme for row in
        (
            db.session.query(Grapheme.grapheme)
            .filter(Grapheme.grapheme.in_(word2phones.keys()))
        )
    )
    return {
        word: phones 
        for word, phones in word2phones.items() 
        if word not in existing_words
    }


def save_word2phones(word2phones: dict[str, str]):
    '''
    Filter out words which are already in the db and change their phones.
    These words can be in the db because we return to a user the same page
    with a file and show the changes the user saved. In this way,
    they can easily edit them if something went wrong.
    '''
    already_existing = []
    words_in_db_rows = (
        db.session.query(Grapheme.id, Grapheme.grapheme, Grapheme.phoneme)
        .filter(Grapheme.grapheme.in_(word2phones))
    )

    for row in words_in_db_rows:
        (Grapheme.query
        .filter(Grapheme.id == row.id)
        .update
        ({Grapheme.phoneme: row.phoneme}, synchronize_session=False))

        grapheme_log = _create_grapheme_log(
            row.id, row.grapheme, 
            from_phoneme=row.phoneme, 
            to_phoneme=word2phones[row.grapheme]
        )

        db.session.add(grapheme_log)
        already_existing.append(row.grapheme)

    for word, phone in word2phones.items():
        if not phone:
            continue
        if word in already_existing:
            continue
        grapheme = Grapheme(grapheme=word, phoneme=phone) 
        db.session.add(grapheme)
        db.session.flush()
            
        grapheme_log = _create_grapheme_log(grapheme.id, grapheme.grapheme, grapheme.phoneme)
        db.session.add(grapheme_log)
