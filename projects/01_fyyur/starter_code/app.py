#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for, abort, jsonify
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *
from datetime import datetime
from models import setup_db, db, Venue, Artist, Show
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
setup_db(app)

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  date = dateutil.parser.parse(value)
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  venues = Venue.query.order_by(Venue.id.desc()).limit(10).all()
  artists = Artist.query.order_by(Artist.id.desc()).limit(10).all()

  venues_format = [venue.format() for venue in venues]
  artists_format = [artist.format() for artist in artists]
  return render_template('pages/home.html', venues=venues_format, artists=artists_format)


#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  '''Display venues data by area
  '''
  venues = Venue.query.order_by('name').all()
  areas = Venue.query.distinct(Venue.city, Venue.state).order_by(Venue.state, Venue.city).all()

  # Retrieve venues by area.
  data = []
  for area in areas:
    data.append({
      'city': area.city,
      'state': area.state,
      'venues': [{
        'id': venue.id,
        'name': venue.name
        } for venue in venues if venue.city == area.city and venue.state == area.state
      ]
    })

  return render_template('pages/venues.html', areas=data);

@app.route('/venues/search', methods=['POST'])
def search_venues():
  '''Search on venues with partial, case-insensitive string search by name, city, or (city, state) pair.
    e.g. seach for Hop should return "The Musical Hop".
    search for "Music" should return "The Musical Hop" and "Park Square Live Music & Coffee"
  '''
  search_term = request.form.get('search_term', '')

  if search_term == '':
    response = {
      'count': 0,
      'data': []
    }
  else:
    # Search venues by name
    venues_by_name = Venue.query.filter(Venue.name.ilike('%{}%'.format(search_term))).order_by(Venue.name).all()

    # Search venues by city or (city, state) pair
    search_term_list = search_term.split(',')
    city = search_term_list[0].strip()

    # check if user only input city
    if len(search_term_list) < 2:
      venues_by_city = Venue.query.filter(Venue.city.ilike(city)).order_by(Venue.name).all()
    # User input (city, state) pair
    else:
      state = search_term_list[1].strip()
      venues_by_city = Venue.query.filter(Venue.city.ilike(city), Venue.state.ilike(state)).order_by(Venue.name).all()
    
    # Combine two search results and remove duplicates
    venues = set(venues_by_name + venues_by_city)

    response = {
      'count': len(venues),
      'data': [venue.format() for venue in venues]
    }

  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  ''' Shows the venue page with the given venue_id
  '''
  venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

  if venue is None:
    abort(404)

  past_shows = Show.query.join(Artist, Show.artist_id == Artist.id).\
    filter(
      Show.venue_id == venue_id, 
      Show.start_time < datetime.now()
    ).\
    order_by(Show.start_time.desc()).all()

  upcoming_shows = Show.query.join(Artist, Show.artist_id == Artist.id).\
    filter(
      Show.venue_id == venue_id, 
      Show.start_time > datetime.now()
    ).\
    order_by(Show.start_time.asc()).all()
  
  # format information for venue detail page
  data = {
    "id": venue.id,
    "name": venue.name,
    "genres": venue.genres.split(','),
    "address": venue.address,
    "city": venue.city,
    "state": venue.state,
    "phone": venue.phone,
    "website": venue.website,
    "facebook_link": venue.facebook_link,
    "seeking_talent": venue.seeking_talent,
    "seeking_description": venue.seeking_description,
    "image_link": venue.image_link,
    "past_shows": [{
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    } for show in past_shows],
    "upcoming_shows": [{
      "artist_id": show.artist_id,
      "artist_name": show.artist.name,
      "artist_image_link": show.artist.image_link,
      "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    } for show in upcoming_shows],
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows)
  }

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  ''' Insert form data as a new Venue record in the db
  '''
  form = VenueForm(request.form, meta={'csrf': False})
  if form.validate():
    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    phone = form.phone.data
    genres = ','.join(form.genres.data)
    facebook_link = form.facebook_link.data
    image_link = form.image_link.data
    website = form.website.data
    seeking_talent = form.seeking_talent.data
    seeking_description = form.seeking_description.data

    if phone == '':
      phone = None

    if facebook_link == '':
      facebook_link = None
    
    if image_link == '':
      image_link = None
    
    if website == '':
      website = None

    if seeking_description == '':
      seeking_description = None

    try:
      venue = Venue(
        name=name, 
        city=city, 
        state=state, 
        address=address, 
        phone=phone, 
        image_link=image_link, 
        facebook_link=facebook_link,
        genres=genres, 
        website=website, 
        seeking_talent=seeking_talent, 
        seeking_description=seeking_description
      )

      venue.insert()
      # on successful db insert, flash success
      flash('Venue ' + request.form['name'] + ' was successfully listed!')
    except ValueError as e:
      print(e)
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
      abort(422)
    finally:
      db.session.close()
  else:
    message = ''
    
    for field, err in form.errors.items():
      message += field + ' ' + '|'.join(err) + '<br/>'
    
    flash('Venue ' + request.form['name'] + ' could not be listed:<br/>' + message)

  return redirect(url_for('index'))

#  Delete Venue
#  ----------------------------------------------------------------

@app.route('/venues/<int:venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  '''Delete a venue with the given venue_id.
  '''
  error = False
  try:
    venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

    if venue is None:
      abort(404)

    venue_name = venue.name
    venue.delete()
    flash("Venue {} has been deleted successfully!".format(venue_name))
  except Exception:
    db.session.rollback()
    error = True
    flash("An error occurred. Venue could not be deleted")
    abort(422)
  finally:
    db.session.close()
  return jsonify({'success': not error})  

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  ''' Display artists data returned from querying the database
  '''
  artists = Artist.query.order_by('name').all()
  data = [artist.format() for artist in artists]

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  '''Search on artists with partial, case-insensitive string search by name, city, or (city, state) pair.
    e.g. seach for "A" should return "Guns N Petals", "Matt Quevado", and "The Wild Sax Band".
    search for "band" should return "The Wild Sax Band".
  '''
  search_term = request.form.get('search_term', '')

  if search_term == '':
    response = {
      'count': 0,
      'data': []
    }
  else:
    # Search artists by name
    artists_by_name = Artist.query.filter(Artist.name.ilike('%{}%'.format(search_term))).order_by(Artist.name).all()

    # Search artists by city or (city, state) pair
    search_term_list = search_term.split(',')
    city = search_term_list[0].strip()

    # check if user only input city
    if len(search_term_list) < 2:
      artists_by_city = Artist.query.filter(Artist.city.ilike(city)).order_by(Artist.name).all()
    # User input (city, state) pair
    else:
      state = search_term_list[1].strip()
      artists_by_city = Artist.query.filter(Artist.city.ilike(city), Artist.state.ilike(state)).order_by(Artist.name).all()
    
    # Combine two search results and remove duplicates
    artists = set(artists_by_name + artists_by_city)

    response = {
      'count': len(artists),
      'data': [artist.format() for artist in artists]
    }

  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  ''' Shows the artist page with the given artist_id
  '''
  artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

  if artist is None:
    abort(404)

  # Retrieve the past shows and upcoming shows of the given artist
  # set two variables, one for the `show` and another for the `venue` 
  # the result of the `JOIN` is a list with a tuple of `show` and `venue`
  past_shows = db.session.query(Show, Venue).join(Venue).\
    filter(
      Show.artist_id == artist_id,
      Show.venue_id == Venue.id,
      Show.start_time < datetime.now()
    ).\
    order_by(Show.start_time.desc()).all()

  upcoming_shows = db.session.query(Show, Venue).join(Venue).\
    filter(
      Show.artist_id == artist_id,
      Show.venue_id == Venue.id,
      Show.start_time > datetime.now()
    ).\
    order_by(Show.start_time.asc()).all()

  # format information for artist detail page
  data = {
    "id": artist.id,
    "name": artist.name,
    "genres": artist.genres.split(','),
    "city": artist.city,
    "state": artist.state,
    "phone": artist.phone,
    "website": artist.website,
    "facebook_link": artist.facebook_link,
    "seeking_venue": artist.seeking_venue,
    "seeking_description": artist.seeking_description,
    "image_link": artist.image_link,
    "past_shows": [{
      "venue_id": show.venue_id,
      "venue_name": venue.name,
      "venue_image_link": venue.image_link,
      "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    } for show, venue in past_shows],
    "upcoming_shows": [{
      "venue_id": show.venue_id,
      "venue_name": venue.name,
      "venue_image_link": venue.image_link,
      "start_time": show.start_time.strftime("%m/%d/%Y, %H:%M")
    } for show, venue in upcoming_shows],
    "past_shows_count": len(past_shows),
    "upcoming_shows_count": len(upcoming_shows)   
  }  

  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  '''Populate form with fields from artist with the given artist_id.
  '''
  form = ArtistForm()
  artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

  if artist is None:
    abort(404)

  form.process(obj=artist)
  form.genres.data = artist.genres.split(',')
  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  ''' Take values from the form submitted, and update existing
    artist record with ID <artist_id> using the new attributes.
  '''
  form = ArtistForm(request.form, meta={'csrf': False})

  # Check input data validation
  if form.validate():
    name = form.name.data
    city = form.city.data
    state = form.state.data
    phone = form.phone.data
    image_link = form.image_link.data
    facebook_link = form.facebook_link.data
    genres = ','.join(form.genres.data)
    website = form.website.data
    seeking_venue = form.seeking_venue.data
    seeking_description = form.seeking_description.data

    if phone == '':
      phone = None

    if facebook_link == '':
      facebook_link = None
    
    if image_link == '':
      image_link = None
    
    if website == '':
      website = None

    if seeking_description == '':
      seeking_description = None

    try:
      artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

      if artist is None:
        abort(404)
      
      artist.name = name 
      artist.city = city
      artist.state = state 
      artist.phone = phone
      artist.image_link = image_link 
      artist.facebook_link = facebook_link
      artist.genres = genres 
      artist.website = website 
      artist.seeking_venue = seeking_venue 
      artist.seeking_description = seeking_description

      artist.update()
      # on successful db update, flash success
      flash('Artist ' + request.form['name'] + ' was successfully updated!')
    except ValueError:
      db.session.rollback()
      # on unsuccessful db update, flash an error instead.
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be updated.')
      abort(422)
    finally:
      db.session.close()
  else:
    message = ''
    
    for field, err in form.errors.items():
      message += field + ' ' + '|'.join(err) + '<br/>'
    
    flash('Artist ' + request.form['name'] + ' could not be updated:<br/>' + message)

  return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  ''' Populate form with values from venue with ID <venue_id>
  '''
  form = VenueForm()
  venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

  if venue is None:
    abort(404)

  form.process(obj=venue)
  form.genres.data = venue.genres.split(',')
  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  ''' Take values from the form submitted, and update existing
    venue record with ID <venue_id> using the new attributes.
  '''
  form = VenueForm(request.form, meta={'csrf': False})
  
  # Check input data validation
  if form.validate():
    name = form.name.data
    city = form.city.data
    state = form.state.data
    address = form.address.data
    phone = form.phone.data
    genres = ','.join(form.genres.data)
    facebook_link = form.facebook_link.data
    image_link = form.image_link.data
    website = form.website.data
    seeking_talent = form.seeking_talent.data
    seeking_description = form.seeking_description.data

    if phone == '':
      phone = None

    if facebook_link == '':
      facebook_link = None
    
    if image_link == '':
      image_link = None
    
    if website == '':
      website = None

    if seeking_description == '':
      seeking_description = None

    try:
      venue = Venue.query.filter(Venue.id == venue_id).one_or_none()

      if venue is None:
        abort(404)
      
      venue.name = name 
      venue.city = city
      venue.state = state 
      venue.address = address 
      venue.phone = phone
      venue.image_link = image_link 
      venue.facebook_link = facebook_link
      venue.genres = genres 
      venue.website = website 
      venue.seeking_talent = seeking_talent 
      venue.seeking_description = seeking_description

      venue.update()
      # on successful db update, flash success
      flash('Venue ' + request.form['name'] + ' was successfully updated!')
    except ValueError:
      db.session.rollback()
      # on unsuccessful db update, flash an error instead.
      flash('An error occurred. Venue ' + request.form['name'] + ' could not be updated.')
      abort(422)
    finally:
      db.session.close()
  else:
    message = ''
    
    for field, err in form.errors.items():
      message += field + ' ' + '|'.join(err) + '<br/>'
    
    flash('Venue ' + request.form['name'] + ' could not be updated:<br/>' + message)

  return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  ''' Insert form data as a new Artist record in the db
  '''
  form = ArtistForm(request.form, meta={'csrf': False})

  if form.validate():
    name = form.name.data
    city = form.city.data
    state = form.state.data
    phone = form.phone.data
    image_link = form.image_link.data
    facebook_link = form.facebook_link.data
    genres = ','.join(form.genres.data)
    website = form.website.data
    seeking_venue = form.seeking_venue.data
    seeking_description = form.seeking_description.data

    if phone == '':
      phone = None

    if facebook_link == '':
      facebook_link = None
    
    if image_link == '':
      image_link = None
    
    if website == '':
      website = None

    if seeking_description == '':
      seeking_description = None

    try:
      artist = Artist(
        name=name, 
        city=city, 
        state=state,  
        phone=phone, 
        image_link=image_link, 
        facebook_link=facebook_link,
        genres=genres, 
        website=website, 
        seeking_venue=seeking_venue, 
        seeking_description=seeking_description
      )

      artist.insert()
      # on successful db insert, flash success
      flash('Artist ' + request.form['name'] + ' was successfully listed!')
    except ValueError as e:
      print(e)
      db.session.rollback()
      # on unsuccessful db insert, flash an error instead.
      flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
      abort(422)
    finally:
      db.session.close()
  else:
    message = ''
    
    for field, err in form.errors.items():
      message += field + ' ' + '|'.join(err) + '<br/>'
    
    flash('Artist ' + request.form['name'] + ' could not be listed:<br/>' + message)

  return redirect(url_for('index'))


#  Delete Artist
#  ----------------------------------------------------------------

@app.route('/artists/<int:artist_id>', methods=['DELETE'])
def delete_artist(artist_id):
  # Take a artist_id, and delete the given artist.
  error = False
  try:
    artist = Artist.query.filter(Artist.id == artist_id).one_or_none()

    if artist is None:
      abort(404)

    artist_name = artist.name
    artist.delete()
    flash("Artist {} has been deleted successfully!".format(artist_name))
  except Exception:
    db.session.rollback()
    error = True
    flash("An error occurred. Artist could not be deleted")
    abort(422)
  finally:
    db.session.close()
  return jsonify({'success': not error})


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  ''' Display list of shows
  '''
  shows = Show.query.join(Venue, Show.venue_id == Venue.id).join(Artist, Show.artist_id == Artist.id).order_by(Show.start_time.desc()).all()
  data = [show.format() for show in shows]

  return render_template('pages/shows.html', shows=data)


#  Create Show
#  ----------------------------------------------------------------

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()
  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  ''' Insert form data as a new Show record in the db
  '''
  form = ShowForm(request.form, meta={'csrf': False})

  # Check if input fields are valid
  if form.validate():
    artist_id = form.artist_id.data
    venue_id = form.venue_id.data
    start_time = form.start_time.data

    artists = Artist.query.all()
    artists_ids = [artist.id for artist in artists]
    venues = Venue.query.all()
    venues_ids = [venue.id for venue in venues]

    artist_exists = artist_id in artists_ids
    venue_exists = venue_id in venues_ids

    # Check if input artist id and venue id exist in tables
    if not artist_exists or not venue_exists:
      flash('Show could not be listed.')
      
      if not artist_exists:
        flash('Artist (id: ' + str(artist_id) + ') does not exist.')
      
      if not venue_exists:
        flash('Venue (id: ' + str(venue_id) + ') does not exist.')
    else:
      try:
        show = Show(
          venue_id=venue_id,
          artist_id=artist_id,
          start_time=start_time
        )

        show.insert()
        # on successful db insert, flash success
        flash('Show was successfully listed!')
      except ValueError as e:
        print(e)
        db.session.rollback()
        # on unsuccessful db insert, flash an error instead.
        flash('An error occurred. Show could not be listed.')
        # see: http://flask.pocoo.org/docs/1.0/patterns/flashing/
        abort(422)
      finally:
        db.session.close()
  else:
    message = ''
    
    for field, err in form.errors.items():
      message += field + ' ' + '|'.join(err) + '<br/>'
    
    flash('Show could not be listed.<br/>' + message)

  return redirect(url_for('index'))


#  Delete Show
#  ----------------------------------------------------------------

@app.route('/shows/<int:show_id>', methods=['DELETE'])
def delete_show(show_id):
  # Take a show_id, and delete the given show.
  error = False
  try:
    show = Show.query.filter(Show.id == show_id).one_or_none()

    if show is None:
      abort(404)

    show.delete()
    flash("Show has been deleted successfully!")
  except Exception:
    db.session.rollback()
    error = True
    flash("An error occurred. Show could not be deleted")
    abort(422)
  finally:
    db.session.close()
  return jsonify({'success': not error})


# Error handlers
#  ----------------------------------------------------------------

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500

@app.errorhandler(400)
def bad_request_error(error):
    return jsonify({
        "success": False, 
        "error": 400,
        "message": "bad request"
    }), 400

@app.errorhandler(405)
def not_allowed_error(error):
    return jsonify({
        'success': False,
        'error': 405,
        'message': 'method not allowed'
    }), 405
  
@app.errorhandler(422)
def unprocessable_error(error):
    return jsonify({
        "success": False, 
        "error": 422,
        "message": "unprocessable"
    }), 422


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
