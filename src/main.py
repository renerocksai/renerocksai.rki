import time
start_time  = time.time()

import sys
import os
from docx import Document
import openai
import faiss
import numpy as np
import pickle
from embedding import EmbeddingCache
from tqdm import tqdm
import textwrap

FILN_FAISS_INDEX = 'faiss.index'
FILN_METADATA = 'metadata.pkl'

if len(sys.argv) != 4:
    print(f'Usage  : python {sys.argv[0]} path/to/data num_results query_text')
    print(f"Example: python {sys.argv[0]} ./data 20 'Lug und Betrug'")
    sys.exit(1)

directory = sys.argv[1]
k_results = int(sys.argv[2])
query_text = sys.argv[3]

embedding_cache = EmbeddingCache()

def textfile_to_paras(filn):
    with open(filn, 'rt') as f:
        lines = [l.strip() for l in f.readlines()]

    paras = []
    current_para = []
    for line in lines:
        if not line:
            paras.append(' '.join(current_para))
            current_para = []
        else:
            current_para.append(line)
    paras.append(' '.join(current_para))
    return paras

def read_text_files_by_paragraph(directory):
    """
    return texts and metadata, where metadata is a tuple of filename,
    paragraph text, and kind. atm kind is always paragraph.
    """
    texts = []
    metadata = []  # To store the document, paragraph/table info, and the text
    print('Loading texts...')
    all_files = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith('.rst'):
                doc_path = os.path.join(dirpath, filename)
                all_files.append(doc_path)
    for doc_path in tqdm(sorted(all_files)):
        # print('Processing', doc_path)
        # Extract paragraphs
        for para in textfile_to_paras(doc_path):
            para = para.strip()
            if para:  # Ensure that the text is not empty
                texts.append(para)
                metadata.append((doc_path, para, "paragraph"))
    return texts, metadata

def get_openai_embeddings(texts, auto_save=False, just_load=False):
    embeddings = []
    if len(texts) > 5:
        print(f'Generating/loading embeddings for {len(texts)} texts...')
        texts = tqdm(texts)
    for index, text in enumerate(texts):
        embedding = embedding_cache.get(text, auto_save=auto_save)
        embeddings.append(embedding)
        if index % 500 == 0 and not just_load:
            print('saving')
            embedding_cache.save_cache()
    return np.array(embeddings)

# by normalizing, we effectively perform a cosine search. see faiss github
def normalize_embeddings(embeddings):
    print('Normalizing embeddings...')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized_embeddings = embeddings / norms
    return normalized_embeddings

def create_faiss_index(embeddings):
    print('Creating FAISS index...')
    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    return index

def search_faiss_index(index, query_embedding, k=5):
    distances, indices = index.search(query_embedding, k)
    return distances, indices

def save_faiss_index(index, filepath):
    faiss.write_index(index, filepath)

def load_faiss_index(filepath):
    print('Loading FAISS index...')
    return faiss.read_index(filepath)

def save_metadata(metadata, filepath):
    with open(filepath, 'wb') as f:
        pickle.dump(metadata, f)

def load_metadata(filepath):
    print('Loading metadata...')
    with open(filepath, 'rb') as f:
        metadata = pickle.load(f)
    return metadata

def show_result(index, distance, meta, width=180):
    filp = meta[0]
    filn = os.path.basename(filp).replace('.rst', '.docx')
    text = meta[1]
    index += 1
    prefix = f'#{index:02} ({distance:5.3f}): {filn:64s} | '
    subsequent_indent = ' ' * (len(prefix) - 2) + '| '
    line = f'{prefix}{text}'
    wrapped_text = textwrap.fill(line, width=width, initial_indent='',
                                 subsequent_indent=subsequent_indent)
    print(wrapped_text)


print(f'Embedding cache holds {len(embedding_cache.values)} unique texts')

if os.path.exists(FILN_METADATA):
    metadata = load_metadata(FILN_METADATA)
else:
    texts, metadata = read_text_files_by_paragraph(directory)
    embeddings = get_openai_embeddings(texts, just_load=False)
    embeddings = normalize_embeddings(embeddings)
    save_metadata(metadata, FILN_METADATA)

if os.path.exists(FILN_FAISS_INDEX):
    # Load FAISS index and metadata
    index = load_faiss_index(FILN_FAISS_INDEX)
else:
    # Create and save FAISS index and metadata
    index = create_faiss_index(embeddings)
    save_faiss_index(index,FILN_FAISS_INDEX)


print(f'\n=== Showing top {k_results} matches for >>>{query_text}<<< ===\n')
query_embedding = get_openai_embeddings([query_text],
                                        just_load=True,
                                        auto_save=True)
query_embedding = normalize_embeddings(query_embedding)
search_start_time = time.time()
distances, indices = search_faiss_index(index, query_embedding, k=k_results)
search_end_time = time.time()

# Retrieve corresponding document filenames and paragraph/table text
result_metadata = [metadata[i] for i in indices[0]]
result_distances = distances[0]
for index, result in enumerate(result_metadata):
    distance= result_distances[index]
    show_result(index, distance, result)
end_time = time.time()
print(f"Search took {search_end_time-search_start_time:0.3f} seconds. {end_time-start_time:0.3f} seconds total.")
