from flask import Flask, request, jsonify
from flask_compress import Compress
import os
from dotenv import load_dotenv
import main

# Load environment variables from the specified .env file if provided
env_file = os.getenv('FLASK_ENV_FILE', None)
if env_file:
    load_dotenv(env_file)
else:
    load_dotenv()  # Load default .env if FLASK_ENV_FILE is not set

datasets_dir = os.getenv('RKI_DATASETS_DIR')
dataset_name = os.getenv('RKI_DATASET')

# N.B. don't save the query embedding cache since its name is fixed here
#      as to avoid conflicts in multiple workers
metadata, faiss_index, q_emb_cache = main.get_resources(datasets_dir,
                                                        dataset_name,
                                                        'query')

app = Flask(__name__)
Compress(app)

app.config['COMPRESS_ALGORITHM'] = 'gzip'
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500

def process_query(query_text, embedding_cache, faiss_index, metadata, 
                  k_results=20,
                  remove_dupes=False,
                  auto_context_size=300,
                  ):
    query_embedding = main.get_query_embeddings(query_text, embedding_cache)
    query_embedding = main.normalize_embeddings(query_embedding)
    faiss_distances, faiss_indices = main.search_faiss_index(faiss_index,
                                                             query_embedding,
                                                             k=k_results)

    result_indices = faiss_indices[0]
    result_distances = faiss_distances[0]

    results = []
    result_texts = []
    for r_no, (idx, dist) in enumerate(zip(result_indices, result_distances)):
        text = metadata[idx].para
        if text in result_texts and remove_dupes:
            continue
        results.append(format_result(r_no, metadata, idx, dist, auto_context_size))
        result_texts.append(text)
    return results

def format_result(result_number, metas, result_index, distance, auto_context_size):
    meta = metas[result_index]
    text = meta.para
    filp = meta.doc_path
    filn = os.path.basename(filp)

    prev_metas = []
    next_metas = []
    total_text = text
    ctx_iter = 0
    prev_exhausted = False
    next_exhausted = False
    while len(total_text) < auto_context_size:
        if prev_exhausted and next_exhausted:
            break
        ctx_iter += 1
        # add context before
        if result_index - ctx_iter >= 0:
            prev = metas[result_index - ctx_iter]
            # if same doc, extract text
            if prev.doc_path == meta.doc_path:
                # only use if text differs from main text
                if prev.para != text:
                    prev_metas.append(prev._asdict())
                    total_text += prev.para
            else:
                prev_exhausted = True
        # add context after
        if result_index + ctx_iter < len(metas):
            next = metas[result_index + ctx_iter]
            # if same doc, extract text
            if next.doc_path == meta.doc_path:
                # only use if text differs from main text
                if next.para != text:
                    next_metas.append(next._asdict())
                    total_text += next.para
            else:
                next_exhausted = True
    prev_metas.reverse()
    ret = {
            'meta': meta._asdict(),
            'prev': prev_metas,
            'next': next_metas,
          }
    return ret


@app.route('/rkiapi/search', methods=['GET'])
def search():
    query = request.args.get('query')
    k_results = request.args.get('k_results')
    remove_dupes = request.args.get('remove_dupes')
    auto_context_size = request.args.get('auto_context_size')

    if not query:
        return jsonify({"error": "query parameter is required"}), 400
    if not k_results:
        return jsonify({"error": "k_results parameter is required"}), 400
    if not remove_dupes:
        return jsonify({"error": "remove_dupes parameter is required"}), 400
    if not auto_context_size:
        return jsonify({"error": "auto_context_size parameter is required"}), 400

    try:
        k_results = int(k_results)
    except:
        return jsonify({"error": "k_results parameter is invalid"}), 400
    try:
        auto_context_size = int(auto_context_size)
    except:
        return jsonify({"error": "auto_context_size parameter is invalid"}), 400

    if remove_dupes != 'true' and remove_dupes != 'false':
        return jsonify({"error": "remove_dupes parameter is invalid"}), 400
    remove_dupes = remove_dupes == 'true'


    return jsonify(process_query(query, q_emb_cache, faiss_index, metadata,
                                 k_results=k_results,
                                 remove_dupes=remove_dupes,
                                 auto_context_size=auto_context_size))

if __name__ == "__main__":
    app.run(debug=True)
