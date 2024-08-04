import os
from flask import Flask, render_template, request, jsonify, g
import requests
from flask_htmx import HTMX
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import uuid


app = Flask(__name__)
htmx = HTMX(app)

# Function to generate a nonce
def generate_nonce():
    return uuid.uuid4().hex

# Middleware to add nonce to the request context
@app.before_request
def add_nonce():
    g.nonce = generate_nonce()

# Middleware to set CSP headers
@app.after_request
def set_csp(response):
    nonce = g.get('nonce', '')
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", 'https://unpkg.com', f"'nonce-{nonce}'"],
        'style-src': ["'self'", "'unsafe-inline'"]
    }
    policy = "; ".join(f"{key} {' '.join(values)}" for key, values in csp.items())
    response.headers['Content-Security-Policy'] = policy
    return response

# Security headers with Talisman
talisman = Talisman(app, force_https=False)


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
    nonce = g.nonce
    return render_template('index.html', nonce=nonce)

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
        api_url = 'http://api-sitzungsprotokolle:5000/rkiapi/search'
    else:
        api_url = 'http://api-zusatzmaterial:5000/rkiapi/search'
    
    try:
        response = requests.get(api_url, params={
            'query': query,
            'k_results': num_results,
            'remove_dupes': remove_dupes,
            'auto_context_size': result_size
        })
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}", flush=True)
        print(f"Response content: {response.content}", flush=True)
        return jsonify({"error": "API request failed"}), 400
    except Exception as err:
        print(f"Other error occurred: {err}", flush=True)  # Python 3.3+ only
        return jsonify({"error": "An error occurred"}), 500

    results = response.json()
    
    # print('API RESULTS', results, flush=True)
    if htmx:
        return render_template('results.html', results=results, nonce=g.nonce)
    else:
        return jsonify(results)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)