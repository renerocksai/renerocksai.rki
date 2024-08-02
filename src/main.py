import time
start_time  = time.time()

import sys
import os
import faiss
import numpy as np
import pickle
from embedding import EmbeddingCache
from tqdm import tqdm
import textwrap

from textloading import read_text_files_by_paragraph
from batchpacking import create_optimal_batches


FILN_FAISS_INDEX = 'faiss.index'
FILN_METADATA = 'metadata.pkl'


def get_openai_embeddings(meta_batches, embedding_cache, auto_save=False, just_load=False, save_every=100):
    embeddings = []
    for index, metas in enumerate(tqdm(meta_batches)):
        sentence_batch = [meta[1] for meta in metas]
        embedding = embedding_cache.get_batch(sentence_batch, auto_save=False)
        embeddings.append(embedding)
        if index % save_every == 0 and not just_load:
            print('saving cache')
            embedding_cache.save_cache()
    return embeddings

def get_query_embeddings(text, embedding_cache):
    embedding = embedding_cache.get(text, auto_save=False)   # TODO: auto_saving takes too long
    # TODO: have a query embedding cache that is separated from the corpora's cache!
    return np.array([embedding])

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
    print('Saving FAISS index...')
    faiss.write_index(index, filepath)

def load_faiss_index(filepath):
    print('Loading FAISS index...')
    return faiss.read_index(filepath)

def save_metadata(metadata, filepath):
    print('Saving metadata...')
    with open(filepath, 'wb') as f:
        pickle.dump(metadata, f)

def load_metadata(filepath):
    print('Loading metadata...')
    with open(filepath, 'rb') as f:
        metadata = pickle.load(f)
    return metadata

def show_result(index, distance, meta, width=180):
    filp = meta[0]
    filn = os.path.basename(filp)
    text = meta[1]
    index += 1
    prefix = f'#{index:02} ({distance:5.3f}): {filn:64s} | '
    subsequent_indent = ' ' * (len(prefix) - 2) + '| '
    line = f'{prefix}{text}'
    wrapped_text = textwrap.fill(line, width=width, initial_indent='',
                                 subsequent_indent=subsequent_indent)
    print(wrapped_text)



if __name__ == '__main__':
    if len(sys.argv) != 4:
        print(f'Usage  : python {sys.argv[0]} path/to/data num_results query_text')
        print(f"Example: python {sys.argv[0]} ./data 20 'Lug und Betrug'")
        sys.exit(1)

    directory = sys.argv[1]
    k_results = int(sys.argv[2])
    query_text = sys.argv[3]

    embedding_cache = EmbeddingCache()
    print(f'Embedding cache holds {len(embedding_cache.values)} unique texts')

    # Load or create metadata, embeddings, faiss index
    if os.path.exists(FILN_METADATA):
        metadata = load_metadata(FILN_METADATA)
        # we assume that embeddings cache is full if we have metadata
        index = load_faiss_index(FILN_FAISS_INDEX)
    else:
        metadata = read_text_files_by_paragraph(directory)

        # fill embeddings cache
        print('Packing batches...')
        metadata_batches = create_optimal_batches(metadata)
        print(f'Generating/loading embeddings for {len(metadata)} texts in {len(metadata_batches)} batches...')
        embedding_batches = get_openai_embeddings(metadata_batches, embedding_cache, just_load=False)

        # now flatten meta and embeddings into flat lists again
        # so they can be accessed by index returned by faiss search
        embeddings = []
        metadata = []
        for meta_batch, embedding_batch in zip(metadata_batches, embedding_batches):
            for meta, embedding in zip(meta_batch, embedding_batch):
                metadata.append(meta)
                embeddings.append(embedding)

        # normalize embeddings before creating the faiss index
        embeddings = np.array(embeddings)
        embeddings = normalize_embeddings(embeddings)
        # save cache after that
        embedding_cache.save_cache()
        save_metadata(metadata, FILN_METADATA)
        index = create_faiss_index(embeddings)
        save_faiss_index(index,FILN_FAISS_INDEX)


    print(f'\n=== Showing top {k_results} matches for >>>{query_text}<<< ===\n')
    query_embedding = get_query_embeddings(query_text, embedding_cache)
    query_embedding = normalize_embeddings(query_embedding)
    search_start_time = time.time()
    distances, indices = search_faiss_index(index, query_embedding, k=k_results)
    search_end_time = time.time()

    # Retrieve corresponding document filenames and paragraph/table text
    result_metadata = [metadata[i] for i in indices[0]]
    result_distances = distances[0]
    for index, result in enumerate(result_metadata):
        distance = result_distances[index]
        show_result(index, distance, result)
    end_time = time.time()
    print(f"Search took {search_end_time-search_start_time:0.3f} seconds. {end_time-start_time:0.3f} seconds total.")
