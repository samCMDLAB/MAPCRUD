from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Map(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sheetname = db.Column(db.String(100), nullable=False)
    sitename = db.Column(db.String(100), nullable=False)
    mapmetadata = db.Column(db.PickleType) 
    data = db.Column(db.PickleType) 
    notes = db.Column(db.PickleType) 
    status = db.Column(db.PickleType) 
    
