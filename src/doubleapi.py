from flask import Flask, request, jsonify
from flask_compress import Compress
import os
from dotenv import load_dotenv
import main


dataset_names = ['sitzungsprotokolle', 'zusatzmaterial', 
                 'corona_BKA', 'corona_BMG_BMI', 'corona_EXP_REGIERUNG',
                 'corona_MPK', 'corona_ALL']

datasets = {}
for dn in dataset_names:
    datasets[f'{dn}'] = {
            'path': os.getenv(f'RKI_DATASETS_DIR'),
            'name' : os.getenv(f'RKI_DATASET_{dn}'),
            }

print('Using datasets', datasets, flush=True)

# N.B. don't save the query embedding cache since its name is fixed here
#      as to avoid conflicts in multiple workers
for dn in dataset_names:
    print('Loading', dn, '...', flush=True)
    metadata, faiss_index, q_emb_cache = main.get_resources(
            datasets[dn]['path'],
            datasets[dn]['name'],
            query_cache_name='query',
            max_cache_size=50,
            )
    datasets[dn]['faiss'] = faiss_index
    datasets[dn]['metadata'] = metadata
    datasets[dn]['qcache'] = q_emb_cache

print('READY.', flush=True)
app = Flask(__name__)
Compress(app)

app.config['COMPRESS_ALGORITHM'] = 'gzip'
app.config['COMPRESS_LEVEL'] = 6
app.config['COMPRESS_MIN_SIZE'] = 500

def process_query(query_text, embedding_cache, faiss_index, metadata,
                  k_results=20,
                  remove_dupes=False,
                  auto_context_size=300,
                  dataset_name=''
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
        results.append(format_result(r_no, metadata, idx, dist,
                                     auto_context_size, dataset=dataset_name))
        result_texts.append(text)
    return results

def cut_prev(prev, current):
    prev = ' '.join(prev.split())
    current = ' '.join(current.split())
    i = 0
    while not current.startswith(prev[i:]):
        i += 1
        if i >= len(prev):
            return prev
    return prev[:i+1]

def cut_next(next, current):
    next = ' '.join(next.split())
    current = ' '.join(current.split())
    i = len(next)
    while not current.endswith(next[:i]):
        i -= 1
        if i == 0:
            return next
    return next[i:]

def format_result(result_number, metas, result_index, distance,
                  auto_context_size, dataset):
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
    safety_net = 0
    while len(total_text) < auto_context_size:
        safety_net += 1
        if safety_net == 10:
            break
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
                    d = prev._asdict()
                    d['para'] = cut_prev(prev.para, text)
                    prev_metas.append(d)
                    total_text += d['para']
            else:
                prev_exhausted = True
        # add context after
        if result_index + ctx_iter < len(metas):
            next = metas[result_index + ctx_iter]
            # if same doc, extract text
            if next.doc_path == meta.doc_path:
                # only use if text differs from main text
                if next.para != text:
                    d = next._asdict()
                    d['para'] = cut_next(next.para, text)
                    next_metas.append(d)
                    total_text += d['para']
            else:
                next_exhausted = True
    prev_metas.reverse()
    meta = meta._asdict()
    meta['dist'] = f'{distance:0.3f}'
    ret = {
            'meta': meta,
            'prev': prev_metas,
            'next': next_metas,
          }
    return ret


@app.route('/rkiapi/search', methods=['GET'])
def search():
    dataset_name = request.args.get('dataset')
    if dataset_name not in dataset_names:
        return jsonify({"error": "dataset name invalid"}), 400
    query = request.args.get('query')
    print('API passthrough:', query, flush=True)
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

    # a bit of sanity
    if k_results > 1000:
        k_results = 1000
    if auto_context_size > 5000:
        auto_context_size = 5000

    q_emb_cache = datasets[dataset_name]['qcache']
    faiss_index = datasets[dataset_name]['faiss']
    metadata = datasets[dataset_name]['metadata']
    return jsonify(process_query(query, q_emb_cache, faiss_index, metadata,
                                 k_results=k_results,
                                 remove_dupes=remove_dupes,
                                 auto_context_size=auto_context_size,
                                 dataset_name=dataset_name))

if __name__ == "__main__":
    app.run(debug=True)
