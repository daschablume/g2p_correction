from app import db

from sqlalchemy import DateTime

from datetime import datetime


# TODO: refactor the models to use the same naming convention
# Grapheme represents a Word, while phoneme represents its transcription
class Grapheme(db.Model):
    __tablename__ = 'graphemes'
    id = db.Column(db.Integer, primary_key=True)
    grapheme = db.Column(db.String, nullable=False, unique=True)
    phoneme = db.Column(db.String, nullable=False)

    __table_args__ = (
        db.Index('grapheme_table_grapheme_index', grapheme),
    )
    
    def __repr__(self):
        return f'Grapheme: <{self.grapheme}>, phoneme=[{self.phoneme}]'


class GraphemeLog(db.Model):
    __tablename__ = 'grapheme_logs'
    id = db.Column(db.Integer, primary_key=True)
    # SET NULL: setting the foreign key to NULL insteading of deleting
    # all the rows that reference the deleted row
    grapheme_id = db.Column(
        db.Integer, db.ForeignKey(Grapheme.id, ondelete='SET NULL')
    )
    grapheme_name = db.Column(db.String, nullable=False, unique=False)
    date_modified = db.Column(
        DateTime, nullable=False, default=datetime.utcnow,
        onupdate=datetime.utcnow
  )
    from_phoneme = db.Column(db.String, nullable=True)
    to_phoneme = db.Column(db.String, nullable=False)

    __table_args__ = (
        db.Index('grapheme_log_grapheme_name_index', grapheme_name),
    )

    def __repr__(self):
        return f'GraphemeLog: id=[{self.id}], grapheme={self.grapheme_name}'