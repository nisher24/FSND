import os
from flask import Flask, request, jsonify, abort
from sqlalchemy import exc
import json
from flask_cors import CORS

from .database.models import db_drop_and_create_all, setup_db, Drink, db
from .auth.auth import AuthError, requires_auth

app = Flask(__name__)
setup_db(app)
CORS(app)

'''
@TODO uncomment the following line to initialize the datbase
!! NOTE THIS WILL DROP ALL RECORDS AND START YOUR DB FROM SCRATCH
!! NOTE THIS MUST BE UNCOMMENTED ON FIRST RUN
'''
# db_drop_and_create_all()


def validate_recipe(recipe):
    '''Validate the format of a drink recipe input.

    Arg:
        recipe: An array of json objects representing ingredients of a drink recipe.

    Returns:
        A boolean value indicating if the recipe format is valid.
    '''
    is_valid = True
    
    for ingredient in recipe:
        if 'name' not in ingredient or 'color' not in ingredient or 'parts' not in ingredient:
            is_valid = False
            break

        if type(ingredient['name']) != str or type(ingredient['color']) != str:
            is_valid = False
            break

        if not (type(ingredient['parts'])== int or type(ingredient['parts'])== float) or ingredient['parts'] <= 0:
            is_valid = False
            break
    
    return is_valid


## ROUTES
'''
    GET /drinks
        it is a public endpoint
        contains only the drink.short() data representation
        returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks')
def get_drinks():
    try:
        drinks = Drink.query.order_by(Drink.id).all()
        drinks_short = [drink.short() for drink in drinks]
    except Exception:
        abort(500)

    return jsonify({
        'success': True,
        'drinks': drinks_short
    })


'''
    GET /drinks-detail
        requires the 'get:drinks-detail' permission
        contains the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drinks} where drinks is the list of drinks
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks-detail')
@requires_auth('get:drinks-detail')
def get_drinks_in_detail(jwt):
    try:
        drinks = Drink.query.order_by(Drink.id).all()
        drinks_long = [drink.long() for drink in drinks]
    except Exception:
        abort(500)

    return jsonify({
        'success': True,
        'drinks': drinks_long
    })


'''
    POST /drinks
        creates a new row in the drinks table
        requires the 'post:drinks' permission
        contains the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the newly created drink
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks', methods=['POST'])
@requires_auth('post:drinks')
def create_drink(jwt):
    error = False
    drink_list = []

    body = request.get_json()
    title = body.get('title', None)
    recipe = body.get("recipe", [])

    if type(recipe) != list:      
        recipe = [recipe]

    # Input validation for recipe
    if not recipe:
        abort(400)

    is_valid = validate_recipe(recipe)
    
    if not is_valid:
        abort(400)
    
    try:
        drink = Drink(title=title, recipe=json.dumps(recipe))
        drink.insert()
        drink_list.append(drink.long())
    # except exc.IntegrityError:
    except Exception:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    
    if error:
        abort(422)
    else:
        return jsonify({
            'success': True,
            'drinks': drink_list
        })


'''
    PATCH /drinks/<id>
        where <id> is the existing model id
        responds with a 404 error if <id> is not found
        updates the corresponding row for <id>
        requires the 'patch:drinks' permission
        contains the drink.long() data representation
    returns status code 200 and json {"success": True, "drinks": drink} where drink an array containing only the updated drink
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks/<int:id>', methods=['PATCH'])
@requires_auth('patch:drinks')
def update_drink(jwt, id):
    error = False
    drink_list = []

    drink = Drink.query.filter(Drink.id == id).one_or_none()

    if drink is None:
        abort(404)

    body = request.get_json()
    title = body.get('title', None)
    recipe = body.get("recipe", [])

    if type(recipe) != list:      
        recipe = [recipe]
    
    # Input validation for recipe
    if recipe:
        is_valid = validate_recipe(recipe)
        
        if not is_valid:
            abort(400)

    try:
        if title:
            drink.title = title
        
        if recipe:
            drink.recipe = json.dumps(recipe)
        
        drink.update()
        drink_list.append(drink.long())
    except Exception:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    
    if error:
        abort(422)
    else:
        return jsonify({
            'success': True,
            'drinks': drink_list
        })

'''
    DELETE /drinks/<id>
        where <id> is the existing model id
        responds with a 404 error if <id> is not found
        deletes the corresponding row for <id>
        requires the 'delete:drinks' permission
    returns status code 200 and json {"success": True, "delete": id} where id is the id of the deleted record
        or appropriate status code indicating reason for failure
'''
@app.route('/drinks/<int:id>', methods=['DELETE'])
@requires_auth('delete:drinks')
def delete_drink(jwt, id):
    error = False
    drink = Drink.query.filter(Drink.id == id).one_or_none()

    if drink is None:
        abort(404)
    
    try:
        drink.delete()
    except Exception:
        error = True
        db.session.rollback()
    finally:
        db.session.close()
    if error:
        abort(422)
    else:
        return jsonify({
            'success': True,
            'delete': id
        })


## Error Handling

@app.errorhandler(422)
def unprocessable(error):
    return jsonify({
        "success": False, 
        "error": 422,
        "message": "unprocessable"
    }), 422

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False, 
        "error": 400,
        "message": "bad request"
    }), 400

@app.errorhandler(401)
def unauthorized(error):
    return jsonify({
        "success": False, 
        "error": 401,
        "message": "unauthorized"
    }), 401

@app.errorhandler(403)
def forbidden(error):
    return jsonify({
        "success": False, 
        "error": 403,
        "message": "forbidden"
    }), 403

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": 404,
        "message": "resource not found"
    }), 404

@app.errorhandler(405)
def not_allowed(error):
    return jsonify({
        'success': False,
        'error': 405,
        'message': 'method not allowed'
    }), 405

@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "success": False,
        "error": 500,
        "message": "internal server error"
    }), 500

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response
