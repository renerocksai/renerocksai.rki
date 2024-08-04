import os
from flask import Flask, render_template, request, jsonify
import requests
from flask_htmx import HTMX
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS

app = Flask(__name__)
htmx = HTMX(app)

# Security headers
Talisman(app, force_https=False)

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Enable CORS if necessary
CORS(app)

# Endpoint to render the main search page
@app.route('/')
@limiter.limit("10 per minute")
def index():
    return render_template('index.html')

# Endpoint to handle search and update the results
@app.route('/search', methods=['GET'])
@limiter.limit("5 per minute")
def search():
    query = request.args.get('query', '')
    dataset = request.args.get('dataset', 'sitzungsprotokolle')
    num_results = request.args.get('num_results', 10)
    remove_dupes = request.args.get('remove_dupes', 'false')
    result_size = request.args.get('result_size', 20)
    
    if dataset == 'sitzungsprotokolle':
        api_url = 'http://api-sitzungsprotokolle:5000/api/search'
    else:
        api_url = 'http://api-zusatzmaterial:5000/api/search'
    
    response = requests.get(api_url, params={
        'query': query,
        'num_results': num_results,
        'remove_dupes': remove_dupes,
        'result_size': result_size
    })
    results = response.json()
    
    if htmx:
        return render_template('results.html', results=results)
    else:
        return jsonify(results)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
