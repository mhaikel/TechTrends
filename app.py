import sqlite3
import datetime
import logging
import sys

from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort

# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    connection = sqlite3.connect('database.db')
    connection.row_factory = sqlite3.Row
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

#function to retrieve the current db connection count from the metrics table
def get_current_db_connection_count(connection):
    metric = 'db_connection_count'
    query = 'SELECT value FROM metrics WHERE name = ?'
    db_connection_count = int(connection.execute(query, (metric,)).fetchone()[0])
    return db_connection_count

#function to update db connection count
def update_db_connection_count(connection):
    query = None
    try:
        # get current db connection count
        current_count = get_current_db_connection_count(connection)
        new_count = current_count + 1
        # update count
        current_time = datetime.datetime.now()
        metric = "db_connection_count"
        query = 'UPDATE metrics SET value = ?, last_updated = ? WHERE name = ?'
        connection.execute(query, (new_count, current_time, metric))
        connection.commit()
    except Exception as er:
        current_time = datetime.datetime.now()
        app.logger.info('%s, Db Connection count update Failed: %s\nError: %s' % (current_time.strftime('%m/%d/%Y, %H:%M:%S'),
                                                             query, str(er)))

def get_post_count(connection):
    query = 'SELECT COUNT(*) FROM posts'
    post_count = int(connection.execute(query).fetchone()[0])
    return post_count

def update_post_count(connection, post_count):
    query = None
    try:
        current_date_time = datetime.datetime.now()
        query = 'UPDATE metrics SET value = ?, last_updated = ? WHERE name = post_count'
        connection.execute(query, (post_count, current_date_time))
        connection.commit()
    except Exception as err:
        current_date_time = datetime.datetime.now()
        app.logger.info('%s, Post Count Update Failed: %s\nError: %s' % ((current_date_time.strftime('%m/%d/%Y, %H:%M:%S'),
                                                              query, str(err))))


# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application 
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered 
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    post = get_post(post_id)
    current_date_time = datetime.datetime.now()
    if post is None:
      app.logger.info("%s, A non-existing article accessed and a 404 page response returned" % (current_date_time.strftime('%m/%d/%Y, %H:%M:%S')))
      return render_template('404.html'), 404
    else:
      app.logger.info('%s, Article "%s" retrieved!' % (current_date_time.strftime('%m/%d/%Y, %H:%M:%S'),
                                                         str(post['title'])))
      return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info('%s, "About Us" page retrieved' % (datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')))
    return render_template('about.html')

# Define the post creation functionality 
@app.route('/create', methods=('GET', 'POST'))
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            update_db_connection_count(connection)
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            app.logger.info('%s, Article "%s" Created!' % (datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S'), str(title)))
            return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/healthz')
def healthz():
    response = app.response_class(
            response=json.dumps({"result":"OK - healthy"}),
            status=200,
            mimetype='application/json'
    )
    return response

@app.route('/metrics')
def metrics():
    connection = None
    try:
        connection = get_db_connection()
        update_db_connection_count(connection)
        current_db_connection_count = get_current_db_connection_count(connection)
        post_count = get_post_count(connection)
        update_post_count(connection, post_count)
        current_date_time = datetime.datetime.now()
        app.logger.info('%s, Metrics request successful' % (current_date_time.strftime('%m/%d/%Y, %H:%M:%S')))
        return app.response_class(
            response=json.dumps({"db_connection_count": current_db_connection_count, "post_count": post_count}),
            status=200,
            mimetype='application/json'
        )
    except Exception as err:
        current_date_time = datetime.datetime.now()
        app.logger.info('%s, %s' % (current_date_time.strftime('%m/%d/%Y, %H:%M:%S'), str(err)))
        print(err)
    finally:
        if connection is not None:
            connection.close()


# start the application on port 3111
if __name__ == "__main__":
    # Stream logs to a file, and set the default log level to DEBUG
   logging.basicConfig(level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        handlers=[
                            logging.StreamHandler(sys.stdout),
                            logging.StreamHandler(sys.stderr)
                            # ,logging.FileHandler('app.log')
                        ])
   app.run(host='0.0.0.0', port='3111')
