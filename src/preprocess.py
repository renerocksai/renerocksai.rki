import sys
import os
import time
import faiss
import numpy as np
import pickle
from embedding import EmbeddingCache
from tqdm import tqdm

from textloading import read_text_files_by_paragraph
from batchpacking import create_optimal_batches


FILN_FAISS_INDEX = 'faiss.index'
FILN_METADATA = 'metadata.pkl'


def get_openai_embeddings(meta_batches, embedding_cache, auto_save=False, just_load=False, save_every=100):
    embeddings = []
    for index, metas in enumerate(tqdm(meta_batches)):
        sentence_batch = [meta.para for meta in metas]
        embedding = embedding_cache.get_batch(sentence_batch, auto_save=False)
        embeddings.append(embedding)
        if index % save_every == 0 and not just_load:
            print('saving cache')
            embedding_cache.save_cache()
    return embeddings

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

def save_faiss_index(index, filepath):
    print('Saving FAISS index...')
    faiss.write_index(index, filepath)

def save_metadata(metadata, filepath):
    print('Saving metadata...')
    with open(filepath, 'wb') as f:
        pickle.dump(metadata, f)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage  : python {sys.argv[0]} path/to/data dataset_name')
        print(f"Example: python {sys.argv[0]} ./data Zusatzpaket")
        sys.exit(1)

    directory = sys.argv[1]
    dataset_name = sys.argv[2]

    filn_metadata = f'{dataset_name}_{FILN_METADATA}'
    filn_faiss = f'{dataset_name}_{FILN_FAISS_INDEX}'

    corpus_embedding_cache = EmbeddingCache(dataset_name)
    print(f'Embedding cache holds {len(corpus_embedding_cache.values)} unique texts')

    metadata = read_text_files_by_paragraph(directory)

    # fill embeddings cache
    print('Packing batches...')
    metadata_batches = create_optimal_batches(metadata)
    print(f'Generating/loading embeddings for {len(metadata)} texts in {len(metadata_batches)} batches...')
    embedding_batches = get_openai_embeddings(metadata_batches, corpus_embedding_cache, just_load=False)

    # now flatten meta and embeddings into flat lists again
    # so they can be accessed by index returned by faiss search
    print('Re-organizing...')
    # Flatten the metadata and embedding batches
    metadata = [meta for batch in metadata_batches for meta in batch]
    embeddings = [embedding for batch in embedding_batches for embedding in batch]
    # Combine metadata and embeddings into a list of tuples
    combined = list(zip(metadata, embeddings))
    # Sort the combined list based on the seq field of the Meta namedtuple
    combined_sorted = sorted(combined, key=lambda x: x[0].seq)
    # Extract the sorted metadata and embeddings
    sorted_metadata = [meta for meta, _ in combined_sorted]
    sorted_embeddings = [embedding for _, embedding in combined_sorted]
    metadata = sorted_metadata
    embeddings = sorted_embeddings

    # normalize embeddings before creating the faiss index
    print('Converting embeddings to numpy...')
    embeddings = np.array(embeddings)
    embeddings = normalize_embeddings(embeddings)

    # save cache after that
    print('Saving embeddings...')
    corpus_embedding_cache.save_cache()
    save_metadata(metadata, filn_metadata)
    faiss_index = create_faiss_index(embeddings)
    save_faiss_index(faiss_index, filn_faiss)

    print(f'Dataset {dataset_name} created!')
