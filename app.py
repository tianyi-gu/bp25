from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import os
from dotenv import load_dotenv


load_dotenv()


base_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = os.path.join(base_dir, 'templates')
static_dir = os.path.join(base_dir, 'static')

os.makedirs(os.path.join(templates_dir), exist_ok=True)
os.makedirs(os.path.join(static_dir, 'css'), exist_ok=True)
os.makedirs(os.path.join(static_dir, 'js'), exist_ok=True)
os.makedirs(os.path.join(templates_dir, 'errors'), exist_ok=True)


if not os.path.exists(os.path.join(templates_dir, 'index.html')):
    with open(os.path.join(templates_dir, 'index.html'), 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title|default('Flask App') }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <main>
        <h1>Welcome to Flask App</h1>
        <p>This is a minimal Flask application.</p>
    </main>
</body>
</html>''')


if not os.path.exists(os.path.join(templates_dir, 'errors', '404.html')):
    with open(os.path.join(templates_dir, 'errors', '404.html'), 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title|default('Page Not Found') }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <main>
        <h1>404 - Page Not Found</h1>
        <p>The page you are looking for does not exist.</p>
        <a href="{{ url_for('index') }}">Return to Home</a>
    </main>
</body>
</html>''')

if not os.path.exists(os.path.join(templates_dir, 'errors', '500.html')):
    with open(os.path.join(templates_dir, 'errors', '500.html'), 'w') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title|default('Server Error') }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
</head>
<body>
    <main>
        <h1>500 - Server Error</h1>
        <p>Something went wrong on our end. Please try again later.</p>
        <a href="{{ url_for('index') }}">Return to Home</a>
    </main>
</body>
</html>''')


app = Flask(__name__, 
            template_folder=templates_dir,
            static_folder=static_dir)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-development')


app.config.update(
    DEBUG=os.environ.get('FLASK_DEBUG', 'True') == 'True',
)


@app.route('/')
def index():
    """Home page route"""
    return render_template('index.html', title='Home')


@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors"""
    return render_template('errors/404.html', title='Page Not Found'), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template('errors/500.html', title='Server Error'), 500


if __name__ == '__main__':
    # Run the app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))