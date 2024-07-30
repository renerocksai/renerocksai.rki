import os
from docx import Document
import openai
import faiss
import numpy as np
import pickle
from embedding import EmbeddingCache
from tqdm import tqdm

FILN_FAISS_INDEX = 'faiss.index'
FILN_METADATA = 'metadata.pkl'

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
                metadata.append((filename, para, "paragraph"))
    return texts, metadata

def get_openai_embeddings(texts):
    embeddings = []
    print(f'Generating/loading embeddings for {len(texts)} texts...')
    for index, text in enumerate(tqdm(texts)):
        embedding = embedding_cache.get(text)
        embeddings.append(embedding)
        if index % 500 == 0:
            embedding_cache.save_cache()
    return np.array(embeddings)

# by normalizing, we effectively perform a cosine search. see faiss github
def normalize_embeddings(embeddings):
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
    with open(filepath, 'rb') as f:
        metadata = pickle.load(f)
    return metadata

directory = './data'
texts, metadata = read_text_files_by_paragraph(directory)
print(f'Embedding cache holds {len(embedding_cache.values)} texts')
embeddings = get_openai_embeddings(texts)
embeddings = normalize_embeddings(embeddings)

if os.path.exists(FILN_FAISS_INDEX):
    # Load FAISS index and metadata
    index = load_faiss_index(FILN_FAISS_INDEX)
    metadata = load_metadata(FILN_METADATA)
else:
    # Create and save FAISS index and metadata
    index = create_faiss_index(embeddings)
    save_faiss_index(index,FILN_FAISS_INDEX)
    save_metadata(metadata,FILN_METADATA)

if len(embeddings) != len(metadata):
    print(f'Documents have been added/deleted. Please remove:')
    print(f'    - {FILN_FAISS_INDEX}')
    print(f'    - {FILN_METADATA}')
    print(f'    - {embedding_cache.cache_file}')

# Example search
query_text = "Lüge"
k_results = 5
query_embedding = get_openai_embeddings([query_text])
distances, indices = search_faiss_index(index, query_embedding, k=k_results)

# Retrieve corresponding document filenames and paragraph/table text
result_metadata = [metadata[i] for i in indices[0]]
for result in result_metadata:
    print(f"Document: {result[0]}, Text: {result[1]}")
