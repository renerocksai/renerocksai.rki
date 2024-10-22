import os
from flask import Flask, render_template, request, jsonify, g, make_response, url_for, redirect, abort, send_from_directory
import requests
from flask_htmx import HTMX
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_compress import Compress
import uuid
from urllib.parse import urlencode, urlunparse

dataset_names = ['sitzungsprotokolle', 'zusatzmaterial', 
                 'corona_BKA', 'corona_BMG_BMI', 'corona_EXP_REGIERUNG',
                 'corona_MPK', 'corona_ALL', 'corona_ABSOLUTELY_EVERYTHING',
                 'pei_files', 'kanzleramt_mails']

app = Flask(__name__)
htmx = HTMX(app)

Compress(app)
app.config['COMPRESS_ALGORITHM'] = 'gzip'
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500

# Middleware to set CSP headers
@app.after_request
def set_csp(response):
    csp = {
        'default-src': ["'self'", ],
        'script-src': ["'self'", ],
        'style-src': ["'self'", "'unsafe-inline'"],
        'frame-src': ["'self'", "https://www.rkileak.com", "https://draftable.com"],  # Allow frames from specific domains

    }
    policy = "; ".join(f"{key} {' '.join(values)}" for key, values in csp.items())
    response.headers['Content-Security-Policy'] = policy
    return response


# Security headers with Talisman
talisman = Talisman(app, force_https=False)

RATE_PER_DAY = 86400
RATE_PER_HOUR = 3600 * 5
RATE_PER_MINUTE = 60 * 5

# Rate limiting
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[f"{RATE_PER_DAY} per day", "{RATE_PER_HOUR} per hour"]
)


# Enable CORS if necessary
CORS(app)




def basename(path):
    if path.endswith('.txt'):
        path = path[:-4]
    return os.path.basename(path)


def get_url_for(doc_path):
    """
    Used as filter in templates to create URLs from doc paths

    data/Sitzungsprotokolle_orig_docx/2022 Original/Ergebnisprotokoll_Lage-AG-Sitzung_2022-08-25.docx.txt
    --> https://www.rkileak.com/view?f=Sitzungsprotokolle/2023/Ergebnisprotokoll_Lage-AG-Sitzung_2023-06-07.docx
    data/Zusatzmaterial 2020-2023/Zusatzmaterial 2020-2023/2020/2020-09-11_Lage-AG/hochladen/20200911_Lagebild Gemeinsamer Krisenstab BMI-BMG.pdf.txt
    --> https://www.rkileak.com/view?f=Zusatzmaterial/2020/2020-09-11_Lage-AG/hochladen/20200911_Lagebild%20Gemeinsamer%20Krisenstab%20BMI-BMG.pdf
    """
    if doc_path.endswith('.txt'):
        doc_path = doc_path[:-4]

    if doc_path.startswith('data/Sitzungsprotokolle'):
        p = doc_path.replace('data/Sitzungsprotokolle_orig_docx/', '')
        dname, rest = os.path.split(p)
        year = dname.replace(' Original', '')
        ret = f'https://www.rkileak.com/view?f=Sitzungsprotokolle/{year}/{rest}'
        return ret
    elif doc_path.startswith('data/Zusatzmaterial 2020-2023/Zusatzmaterial 2020-2023/'):
        p = doc_path.replace('data/Zusatzmaterial 2020-2023/Zusatzmaterial 2020-2023/', '')
        ret = f'https://www.rkileak.com/view?f=Zusatzmaterial/{p}'
        return ret
    elif doc_path.startswith('data/corona-protokolle/'):
        p = os.path.basename(doc_path)
        if 'BMI' in p:
            p = 'BMG_BMI/Protokolle BMG BMI Gemeinsamer Corona Krisenstab.pdf'
        elif 'Bundeskanzleramt' in p:
            p = 'Bundeskanzleramt/Protokolle Bundeskanzleramt Corona Krisenstab.pdf'
        elif 'kanzlerin' in p:
            p = 'MPK/Protokolle Kanzlerin Ministerpräsidenten Konferenz.pdf'
        elif 'Coronaexpertendezember_ocr' in p:
            p = 'Expertenrat/Protokolle ExpertInnenrat der Bundesregierung zur COVID-19 Pandemie.pdf'
        return f'https://www.rkileak.com/view?f={p}'
    elif doc_path.startswith('data/pei-files'):
        return url_for('view_pdf', dataset='pei_files', filn=os.path.basename(doc_path))
    elif doc_path.startswith('./data/kanzleramt-mails'):
        return url_for('view_pdf', dataset='kanzleramt_mails', filn=os.path.basename(doc_path))
    return '#'


def get_path_for(doc_path):
    if doc_path.endswith('.txt'):
        doc_path = doc_path[:-4]

    if doc_path.startswith('data/Sitzungsprotokolle'):
        ret = doc_path.replace('data/', '')
        return ret
    elif doc_path.startswith('data/Zusatzmaterial 2020-2023/Zusatzmaterial 2020-2023/'):
        ret = doc_path.replace('data/Zusatzmaterial 2020-2023', '')
        return ret
    elif doc_path.startswith('data/corona-protokolle/'):
        ret = doc_path.replace('data/corona-protokolle/', '')
        ret = os.path.basename(ret)
        if 'BMI' in ret:
            ret = 'Protokolle BMG BMI Gemeinsamer Corona Krisenstab.pdf'
        elif 'Bundeskanzleramt' in ret:
            ret = 'Protokolle Bundeskanzleramt Corona Krisenstab.pdf'
        elif 'kanzlerin' in ret:
            ret = 'Protokolle Kanzlerin Ministerpräsidenten Konferenz.pdf'
        elif 'Coronaexpertendezember_ocr' in ret:
            ret = 'Protokolle ExpertInnenrat der Bundesregierung zur COVID-19 Pandemie.pdf'
        return ret
    elif doc_path.startswith('data/pei-files'):
        return doc_path.replace('data/pei-files/', '')
    elif doc_path.startswith('./data/kanzleramt-mails'):
        return doc_path.replace('./data/kanzleramt-mails/', '')
    return '#'

def get_foreign_path(doc_path):
    if doc_path.endswith('.txt'):
        doc_path = doc_path[:-4]

    if doc_path.startswith('data/Sitzungsprotokolle'):
        p = doc_path.replace('data/Sitzungsprotokolle_orig_docx/', '')
        dname, rest = os.path.split(p)
        year = dname.replace(' Original', '')
        ret = f'Sitzungsprotokolle/{year}/{rest}'
        return ret
    elif doc_path.startswith('data/Zusatzmaterial 2020-2023/Zusatzmaterial 2020-2023/'):
        p = doc_path.replace('data/Zusatzmaterial 2020-2023/Zusatzmaterial 2020-2023/', '')
        ret = f'Zusatzmaterial/{p}'
        return ret
    elif doc_path.startswith('data/corona-protokolle/'):
        p = os.path.basename(doc_path)
        if 'BMI' in p:
            p = 'Protokolle BMG BMI Gemeinsamer Corona Krisenstab.pdf'
        elif 'Bundeskanzleramt' in p:
            p = 'Protokolle Bundeskanzleramt Corona Krisenstab.pdf'
        elif 'kanzlerin' in p:
            p = 'Protokolle Kanzlerin Ministerpräsidenten Konferenz.pdf'
        elif 'Coronaexpertendezember_ocr' in p:
            p = 'Protokolle ExpertInnenrat der Bundesregierung zur COVID-19 Pandemie.pdf'
        return p
    return '#'

app.jinja_env.filters['basename'] = basename
app.jinja_env.filters['docurl'] = get_url_for
app.jinja_env.filters['docpath'] = get_path_for


def url_for_external(base_url, **params):
    """
    Create a URL with query parameters for an external service.
    
    :param base_url: The base URL for the external service (e.g., 'https://x.com/intent/tweet').
    :param params: Key-value pairs of query parameters to include in the URL.
    :return: A complete URL with encoded query parameters.
    """
    query_string = urlencode(params)
    return urlunparse(('https', base_url, '', '', query_string, ''))


# Endpoint to render the main search page
@app.route('/', methods=['GET'])
@limiter.limit(f"{RATE_PER_MINUTE} per minute")
def index():
    return render_template('index.html')


@app.route('/corona-protokolle', methods=['GET'])
@limiter.limit(f"{RATE_PER_MINUTE} per minute")
def corona_index():
    # phase out the special casing
    return redirect(url_for('index'))


# Endpoint to handle search and update the results
@app.route('/search', methods=['GET'])
@limiter.limit(f"{RATE_PER_MINUTE} per minute")
def search():
    query = request.args.get('query', '')
    query = query[:300]
    dataset = request.args.get('dataset', 'sitzungsprotokolle')
    num_results = request.args.get('num_results', 10)
    remove_dupes = request.args.get('remove_dupes', None)
    if remove_dupes:
        remove_dupes = 'true'
    else:
        remove_dupes = 'false'
    result_size = request.args.get('result_size', 20)

    if dataset not in dataset_names:
        dataset = 'sitzungsprotokolle'

    api_url = 'http://api:5000/rkiapi/search'

    try:
        response = requests.get(api_url, params={
            'dataset': dataset,
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
        print(f"Other error occurred: {err}", flush=True)
        return jsonify({"error": "An error occurred"}), 500

    results = response.json()
    permalink=url_for('search', query=query, dataset=dataset, 
                      num_results=num_results, remove_dupes=remove_dupes,
                      result_size=result_size,
                      _external=True)
    permalink = permalink.replace('http://', 'https://')
    tweet_text=f'Sucht mal nach 🔎 "{query}" in den Corona-Files: 🔗'
    if 'corona_' in dataset:
        tweet_text=f'Sucht mal nach 🔎 "{query}" in den Corona-Files: 🔗'
    if 'pei_' in dataset:
        tweet_text=f'Sucht mal nach 🔎 "{query}" in den PEI-Files: 🔗'

    twitterlink = url_for_external(
        'x.com/intent/tweet',
        text=tweet_text,
        url=permalink,
    )
    return render_template('index.html', results=results,
                           permalink=permalink,
                           twitterlink=twitterlink,
                           query=query,
                           dataset=dataset,
                           num_results=num_results,
                           remove_dupes=remove_dupes,
                           result_size=result_size,
                           )


# Endpoint to handle PDF upstream for preview
@app.route('/view_pdf', methods=['GET'])
@limiter.limit(f"{RATE_PER_MINUTE} per minute")
def view_pdf():
    dataset = request.args.get('dataset', None)
    filn = request.args.get('filn', None)
    
    if (dataset is None) or (filn is None):
        abort(404)

    return render_template('view_pdf.html',
                           dataset=dataset,
                           filn=filn,
                           )


# Endpoint to handle PDF upstream for preview
@app.route('/pdf/<dataset>/<filn>', methods=['GET'])
@limiter.limit(f"{RATE_PER_MINUTE} per minute")
def serve_pdf(dataset, filn):
    if dataset not in dataset_names:
        print("DATASET NAME INVALID", flush=True)
        abort(404)
    file_path = os.path.join(app.static_folder, dataset, filn)
    if not os.path.exists(file_path):
        print("FILE DOES NOT EXIST", dataset, filn, flush=True)
        abort(404)

    render_path = os.path.join(dataset, filn)
    return send_from_directory(app.static_folder, render_path)


# Custom 404 error handler
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# API pass-through endpoint
@app.route('/rkileaks_api', methods=['GET'])
@limiter.limit("60 per minute")
def api():
    api_url = 'http://api:5000/rkiapi/search'
    query_params = request.args.to_dict()
    try:
        response = requests.get(api_url, params=query_params)
        response.raise_for_status()  # Raise an exception for HTTP errors
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}", flush=True)
        print(f"Response content: {response.content}", flush=True)
        return jsonify({"error": "API request failed"}), 400
    except Exception as err:
        print(f"Other error occurred: {err}", flush=True)  # Python 3.3+ only
        return jsonify({"error": "An error occurred"}), 500

    # Handle JSON response content
    json_result = []
    try:
        json_data = response.json()
        for result in json_data:
            meta = result['meta']
            meta['doc_path'] = get_foreign_path(meta['doc_path'])

            p = result['prev']
            new_prev = []
            for d in p:
                d['doc_path'] = get_foreign_path(d['doc_path'])
                new_prev.append(d)
            new_next = []
            n = result['next']
            for d in n:
                d['doc_path'] = get_foreign_path(d['doc_path'])
                new_next.append(d)
            new_result = {
                    'meta': meta,
                    'prev': new_prev,
                    'next': new_next,
                    }
            json_result.append(new_result)

    except ValueError as json_err:
        print(f"JSON decode error: {json_err}", flush=True)
        return jsonify({"error": "Failed to decode JSON response"}), 500

    
    # Create a response object using the JSON data
    flask_response = make_response(jsonify(json_result), response.status_code)
    for key, value in response.headers.items():
        if key.lower() not in ['content-length', 'content-encoding']:
            flask_response.headers[key] = value

    return flask_response

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80)
