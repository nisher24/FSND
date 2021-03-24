from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()

#----------------------------------------------------------------------------#
# setup_db(app)
#     binds a flask application and a SQLAlchemy service
#----------------------------------------------------------------------------#

def setup_db(app):
    db.app = app
    db.init_app(app)
    migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# CRUDMethods
#----------------------------------------------------------------------------#
class CRUDMethods(db.Model):
    '''
    Extend the base Model class to add common methods
    '''
    __abstract__ = True

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def update(self):
        db.session.commit()

#----------------------------------------------------------------------------#
# Venue
#----------------------------------------------------------------------------#

class Venue(CRUDMethods):
    __tablename__ = 'venues'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String(120), nullable=False)
    state = Column(String(120), nullable=False)
    address = Column(String(120), nullable=False)
    phone = Column(String(120))
    image_link = Column(String(500))
    facebook_link = Column(String(120))
    genres = Column(String(255), nullable=False)
    website = Column(String(120))
    seeking_talent = Column(Boolean, nullable=False, default=False)
    seeking_description = Column(String)

    shows = db.relationship('Show', backref='venue', lazy=True, cascade='all, delete-orphan')

    def __init__(self, name, city, state, address, phone, image_link, facebook_link, genres, website, seeking_talent, seeking_description):
        self.name = name
        self.city = city
        self.state = state
        self.address = address
        self.phone = phone
        self.image_link = image_link
        self.facebook_link = facebook_link
        self.genres = genres
        self.website = website
        self.seeking_talent = seeking_talent
        self.seeking_description = seeking_description
    
    def format(self):
        return {
            'id': self.id,
            'name': self.name
        } 

#----------------------------------------------------------------------------#
# Artist
#----------------------------------------------------------------------------#

class Artist(CRUDMethods):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    city = Column(String(120), nullable=False)
    state = Column(String(120), nullable=False)
    phone = Column(String(120))
    genres = Column(String(255), nullable=False)
    image_link = Column(String(500))
    facebook_link = Column(String(120))
    website = Column(String(120))
    seeking_venue = Column(Boolean, nullable=False, default=False)
    seeking_description = Column(String)

    shows = db.relationship('Show', backref='artist', lazy=True, cascade='all, delete-orphan')

    def __init__(self, name, city, state, phone, image_link, facebook_link, genres, website, seeking_venue, seeking_description):
        self.name = name
        self.city = city
        self.state = state
        self.phone = phone
        self.image_link = image_link
        self.facebook_link = facebook_link
        self.genres = genres
        self.website = website
        self.seeking_venue = seeking_venue
        self.seeking_description = seeking_description

    def format(self):
        return {
          'id': self.id,
          'name': self.name
        } 

#----------------------------------------------------------------------------#
# Show
#----------------------------------------------------------------------------#

class Show(CRUDMethods):
    __tablename__ = 'shows'

    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('venues.id'), nullable=False)
    artist_id = Column(Integer, ForeignKey('artists.id'), nullable=False)
    start_time = Column(DateTime, nullable=False)

    def __init__(self, venue_id, artist_id, start_time):
      self.venue_id = venue_id
      self.artist_id = artist_id
      self.start_time = start_time
    
    # Retrieve a show joining venues and artists tables
    # to show venue and artist names and artist image link.
    def format(self):
        return {
            "id": self.id,
            "venue_id": self.venue_id,
            "venue_name": self.venue.name,
            "artist_id": self.artist_id,
            "artist_name": self.artist.name,
            "artist_image_link": self.artist.image_link,
            "start_time": str(self.start_time)
        }