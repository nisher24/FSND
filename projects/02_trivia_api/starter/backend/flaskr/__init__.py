import os
from flask import Flask, request, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import random
# from sqlalchemy.sql import func

from models import setup_db, Question, Category

QUESTIONS_PER_PAGE = 10

# Paginate questions


def paginate_quesions(request):
    page = request.args.get('page', 1, type=int)
    current_index = page - 1

    questions = Question.query.order_by(
        Question.id).offset(
        current_index *
        QUESTIONS_PER_PAGE).limit(QUESTIONS_PER_PAGE).all()

    questions_format = [question.format() for question in questions]
    return questions_format

# Format categories to a dictionary


def format_categories(categories):
    categories_format = [category.format() for category in categories]
    categories_dict = {str(category["id"]): category["type"]
                       for category in categories_format}

    return categories_dict


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__)
    setup_db(app)

    cors = CORS(app, resources={r"/*": {"origins": "*"}})

    '''
    Use the after_request decorator to set Access-Control-Allow
    '''
    # CORS Headers
    @app.after_request
    def after_request(response):
        response.headers.add(
            'Access-Control-Allow-Headers',
            'Content-Type, Authorization, true')
        response.headers.add(
            'Access-Control-Allow-Methods',
            'GET, PUT, POST, DELETE, PATCH, OPTIONS')
        return response

    '''
    endpoint to handle GET requests
    for all available categories.
    '''
    # Route for retrieving all categories
    @app.route('/categories')
    def get_categories():
        categories = Category.query.order_by(Category.id).all()
        categories_dict = format_categories(categories)

        return jsonify({
            'success': True,
            'categories': categories_dict
        })

    '''
    Endpoint to handle GET requests for questions,
    including pagination (every 10 questions).
    This endpoint returns a list of questions,
    number of total questions, current category, categories.

    TEST: At this point, when you start the application
    you should see questions and categories generated,
    ten questions per page and pagination at the bottom of
    the screen for three pages.
    Clicking on the page numbers should update the questions.
    '''
    # Route for getting paginated questions
    @app.route('/questions')
    def get_questions():
        current_questions = paginate_quesions(request)

        categories = Category.query.order_by(Category.id).all()
        categories_dict = format_categories(categories)

        if len(current_questions) == 0:
            abort(404)

        return jsonify({
            'success': True,
            'questions': current_questions,
            'total_questions': Question.query.count(),
            'categories': categories_dict,
            'current_category': None
        })

    '''
    Endpoint to DELETE question using a question ID.

    TEST: When you click the trash icon next to a question,
    the question will be removed.
    This removal will persist in the database and when you refresh the page.
    '''
    # Route for deleting a question
    @app.route('/questions/<int:question_id>', methods=['DELETE'])
    def delete_question(question_id):
        try:
            question = Question.query.filter(
                Question.id == question_id).one_or_none()

            if question is None:
                abort(404)

            question.delete()

            return jsonify({
                'success': True,
                'delete': question.id
            })

        except Exception:
            abort(422)

    '''
    Endpoint to POST a new question,
    which will require the question and answer text,
    category, and difficulty score.

    TEST: When you submit a question on the "Add" tab,
    the form will clear and the question will appear at the end of the
    last page of the questions list in the "List" tab.
    '''
    # Route for adding a new question
    @app.route('/questions', methods=['POST'])
    def create_question():
        body = request.get_json()

        new_question = body.get('question', None)
        new_answer = body.get('answer', None)
        new_difficulty = body.get('difficulty', None)
        new_category = body.get('category', None)

        try:
            question = Question(
                question=new_question,
                answer=new_answer,
                category=new_category,
                difficulty=new_difficulty)
            question.insert()

            return jsonify({
                'success': True,
                'created': question.id
            })

        except Exception:
            abort(422)

    '''
    POST endpoint to get questions based on a search term.
    It should return any questions for whom the search term
    is a substring of the question.

    TEST: Search by any phrase. The questions list will update to include
    only question that include that string within their question.
    Try using the word "title" to start.
    '''
    # Route for getting questions based on a search term
    @app.route('/questions/search', methods=['POST'])
    def get_questions_by_search_term():
        body = request.get_json()
        search_term = body.get('searchTerm', None)

        questions = Question.query.filter(
            Question.question.ilike(
                '%{}%'.format(search_term))).order_by(
            Question.id).all()
        questions_format = [question.format() for question in questions]

        if len(questions_format) == 0:
            abort(404)

        return jsonify({
            'success': True,
            'questions': questions_format,
            'total_questions': len(Question.query.all()),
            'current_category': None
        })

    '''
    GET endpoint to get questions based on category.

    TEST: In the "List" tab / main screen, clicking on one of the
    categories in the left column will cause only questions of that
    category to be shown.
    '''
    # Route for getting questions based on category
    @app.route('/categories/<category_id>/questions')
    def get_questions_by_category(category_id):
        questions = Question.query.filter(
            Question.category == category_id).order_by(
            Question.id).all()
        questions_format = [question.format() for question in questions]

        if len(questions_format) == 0:
            abort(404)

        current_category = questions_format[0]['category']

        return jsonify({
            'success': True,
            'questions': questions_format,
            'total_questions': len(Question.query.all()),
            'current_category': int(current_category)
        })

    '''
    POST endpoint to get questions to play the quiz.
    This endpoint takes category and previous question parameters
    and returns a random questions within the given category,
    if provided, and that is not one of the previous questions.

    TEST: In the "Play" tab, after a user selects "All" or a category,
    one question at a time is displayed, the user is allowed to answer
    and shown whether they were correct or not.
    '''
    # Route for getting a random quiz question within the given category
    # , if provided, and that is not one of the previous questions
    @app.route('/quizzes', methods=['POST'])
    def get_quizzes():
        body = request.get_json()

        quiz_category = body.get('quiz_category', None)
        previous_questions = body.get('previous_questions', None)

        if quiz_category['id'] == 0:
            # question = Question.query.filter(
            # ~Question.id.in_(previous_questions)).order_by(
            # func.random()).first()
            questions = Question.query.filter(
                ~Question.id.in_(previous_questions)).all()
        else:
            category = Category.query.filter(
                Category.id == int(
                    quiz_category['id'])).one_or_none()

            if category is None:
                abort(404)

            # question = Question.query.filter(
            # Question.category == quiz_category['id'], ~Question.id.in_(
            # previous_questions)).order_by(func.random()).first()
            questions = Question.query.filter(
                Question.category == quiz_category['id'],
                ~Question.id.in_(previous_questions)).all()

        # if question is not None:
        #   question = question.format()
        if len(questions) > 0:
            question = random.choice(questions).format()
        else:
            question = None

        return jsonify({
            'success': True,
            'question': question
        })

    # Route for adding a new category
    @app.route('/categories', methods=['POST'])
    def create_category():
        body = request.get_json()
        new_type = body.get('type', None)

        try:
            category = Category(type=new_type)
            category.insert()

            return jsonify({
                'success': True,
                'created': category.id
            })

        except Exception:
            abort(422)

    '''
    Error handlers for all expected errors
    '''
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "success": False,
            "error": 400,
            "message": "bad request"
        }), 400

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

    @app.errorhandler(422)
    def unprocessable(error):
        return jsonify({
            "success": False,
            "error": 422,
            "message": "unprocessable"
        }), 422

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({
            "success": False,
            "error": 500,
            "message": "internal server error"
        }), 500

    return app
