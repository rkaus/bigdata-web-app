from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
import requests
import os
import logging
import pika
import json
import time

logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
logging.basicConfig(filename='app.log', level=logging.INFO)

app = Flask(__name__, template_folder=os.path.abspath('templates'))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///recipes.db'

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return '<User %r>' % self.username

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
    ingredients = db.Column(db.Text)
    url = db.Column(db.String(500))
    calories = db.Column(db.Integer)
    cuisine_type = db.Column(db.String(100))

with app.app_context():
    db.create_all()

credentials = pika.PlainCredentials('user', 'password')
# Establish connection to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost',port=5672,credentials=credentials,heartbeat=600))
channel = connection.channel()

# Declare the recipe queue
recipe_queue = 'recipe_queue'
channel.queue_declare(queue=recipe_queue)

# Declare the analysis result queue
analysis_queue = 'analysis_queue'
channel.queue_declare(queue=analysis_queue)



@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        keyword = request.form['keyword']
        recipes = search(keyword)

        # publish_recipes(recipes,keyword)
        # analysis_result = consume_and_analyze(keyword)
        analysis_result = analyze_results(recipes)
        return render_template('results.html', recipes=recipes, analysis_result=analysis_result)

    return render_template('index.html')

def search(keyword):
    app_id = '3eb0f9c1'
    app_key = 'ff03949c31ebfe8b25326e17164c036c'
    url = f'https://api.edamam.com/search?q={keyword}&app_id={app_id}&app_key={app_key}&to=10'

    response = requests.get(url)

    if response.status_code != 200:
        return render_template('error.html', message='Failed to fetch recipes from the API.')

    data = response.json()
    recipes = []

    try:
        for hit in data.get('hits', []):
            recipe = hit.get('recipe')
            if recipe:
                round_calories = round(recipe.get('calories',0))
                recipe_info = {
                    'name': recipe.get('label'),
                    'ingredients': ", ".join(recipe.get('ingredientLines', [])),
                    'url': recipe.get('url'),
                    'calories': round_calories,
                    'cuisine_type': ', '.join(recipe.get('cuisineType', ['N/A']))
                }
                recipes.append(recipe_info)

                db_recipe = Recipe(
                    name=recipe_info['name'],
                    ingredients=recipe_info['ingredients'],
                    url=recipe_info['url'],
                    calories=round(recipe_info['calories'],0),
                    cuisine_type=recipe_info['cuisine_type'])
                db.session.add(db_recipe)
                db.session.commit()

    except Exception as e:
        app.logger.error(f"Error occurred: {str(e)}")
        db.session.rollback()
        return render_template('error.html', message=f"An error occurred while processing the request. {str(e)}")

    finally:
        db.session.close()

    return recipes
    # return render_template('results.html', recipes=recipes)


@app.route('/health')
def health_check():
    return 'OK', 200


# def analyze_results(recipes):
#     total_recipes = len(recipes)
#     total_calories = sum(recipe['calories'] for recipe in recipes)
#     average_calories = total_calories / total_recipes if total_recipes > 0 else 0
#
#     # Determine the most common cuisine types
#     cuisine_counter = {}
#     for recipe in recipes:
#         cuisine_types = recipe['cuisine_type'].split(', ')
#         for cuisine in cuisine_types:
#             cuisine_counter[cuisine] = cuisine_counter.get(cuisine, 0) + 1
#     most_common_cuisine = max(cuisine_counter, key=cuisine_counter.get) if cuisine_counter else None
#
#     analysis_result = {
#         'total_recipes': total_recipes,
#         'total_calories': total_calories,
#         'average_calories': average_calories,
#         'most_common_cuisine': most_common_cuisine
#     }
#
#     return analysis_result

#
# def analyze_results(recipes):
#     valid_recipes = [recipe for recipe in recipes if isinstance(recipe, dict)]
#
#     total_recipes = len(valid_recipes)
#     total_calories = sum(recipe['calories'] for recipe in valid_recipes)
#     average_calories = total_calories / total_recipes if total_recipes > 0 else 0
#
#     cuisine_counter = {}
#     for recipe in valid_recipes:
#         cuisine_types = recipe['cuisine_type'].split(', ')
#         for cuisine in cuisine_types:
#             cuisine_counter[cuisine] = cuisine_counter.get(cuisine, 0) + 1
#     most_common_cuisine = max(cuisine_counter, key=cuisine_counter.get) if cuisine_counter else None
#
#     analysis_result = {
#         'total_recipes': total_recipes,
#         'total_calories': total_calories,
#         'average_calories': average_calories,
#         'most_common_cuisine': most_common_cuisine
#     }
#
#     return analysis_result

def analyze_results(recipes):
    # valid_recipes = [recipe for recipe in recipes if isinstance(recipe, dict)]
    valid_recipes = recipes

    total_recipes = len(valid_recipes)
    total_calories = sum(recipe.get('calories', 0) for recipe in valid_recipes)
    average_calories = total_calories / total_recipes if total_recipes > 0 else 0

    cuisine_counter = {}
    for recipe in valid_recipes:
        cuisine_types = recipe.get('cuisine_type', '').split(', ')
        for cuisine in cuisine_types:
            cuisine_counter[cuisine] = cuisine_counter.get(cuisine, 0) + 1
    most_common_cuisine = max(cuisine_counter, key=cuisine_counter.get) if cuisine_counter else None

    analysis_result = {
        'total_recipes': total_recipes,
        'total_calories': total_calories,
        'average_calories': average_calories,
        'most_common_cuisine': most_common_cuisine
    }

    return analysis_result


def publish_recipes(recipes, keyword):
    current_time = int(time.time())
    for recipe in recipes:
        message = {
            'recipe': recipe,
            'timestamp': current_time,
            'keyword': keyword
        }
        channel.basic_publish(exchange='', routing_key=recipe_queue, body=json.dumps(message))

def consume_and_analyze(keyword):
    analysis_results = []
    messages = []
    all_recipes=[]

    for method_frame, properties, body in channel.consume(recipe_queue, auto_ack=True):
        message = json.loads(body)
        if message['keyword'] == keyword:
            messages.append(message)
        # channel.basic_cancel(method_frame.consumer_tag)

    # Sort messages by timestamp (most recent first)
    messages.sort(key=lambda x: x['timestamp'], reverse=True)

    # Process the most recent messages related to the keyword
    for message in messages:
        all_recipes.append(message['recipe'])
        # analysis_result = analyze_results(message['recipe'])
        # analysis_results.append(analysis_result)

    analysis_results = analyze_results(all_recipes)
    return analysis_results


# def consume_and_analyze(recent_keyword):
#     all_recipes = []
#
#     # Read all messages from the queue
#     for method_frame, properties, body in channel.consume(recipe_queue, auto_ack=True):
#         keyword = properties.headers.get('keyword')
#         if keyword == recent_keyword:
#             recipes = json.loads(body)
#             all_recipes.extend(recipes)
#
#     # Analyze all collected recipes
#     analysis_result = analyze_results(all_recipes)
#
#     # Publish analysis results to the analysis queue
#     channel.basic_publish(exchange='', routing_key=analysis_queue, body=json.dumps(analysis_result))
#
#     return analysis_result

# def consume_and_analyze():
#     analysis_results = []
#     for method_frame, properties, body in channel.consume(recipe_queue):
#         recipes = json.loads(body)
#         analysis_result = analyze_results(recipes)
#         analysis_results.append(analysis_result)
#         channel.basic_publish(exchange='', routing_key=analysis_queue, body=json.dumps(analysis_result))
#         if len(analysis_results) >= len(recipes):
#             break
#     return analysis_results

if __name__ == '__main__':
    app.run(debug=True)
