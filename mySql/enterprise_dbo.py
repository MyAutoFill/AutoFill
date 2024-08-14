"""EnterpriseData model definition."""

from mySql.database import db

class EnterpriseData(db.Model):
    """Model for EnterpriseData."""

    __tablename__ = 'EnterpriseData'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    EnterpriseId = db.Column(db.BigInteger, nullable=False)
    date = db.Column(db.BigInteger, nullable=False)
    Platform = db.Column(db.String(255), nullable=False)
    TableName = db.Column(db.String(255), nullable=False)
    Data = db.Column(db.JSON, nullable=False)
    SchemaVersion = db.Column(db.Integer, nullable=False)
