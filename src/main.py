import sys
import os
import time
import faiss
import numpy as np
import pickle
from embedding import EmbeddingCache
from tqdm import tqdm
import textwrap
import shutil

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


def show_result(result_number, metas, result_index, distance,
                max_filn_len=64,
                output_width=180, 
                num_contexts_before=1,
                num_contexts_after=1,
                highlight_on='>>>',
                highlight_off='',
                context_on='   ',
                context_off='',
                auto_contexts = False,
                ):
    result_number += 1
    meta = metas[result_index]
    text = meta.para
    filp = meta.doc_path
    filn = os.path.basename(filp)

    output_tuples = []
    if auto_contexts:
        total_text = text
        if auto_contexts == True:
            desired_length = output_width
        else:
            desired_length = auto_contexts
        ctx_iter = 0
        prev_exhausted = False
        next_exhausted = False
        prev_ctx = []
        next_ctx = []
        while len(total_text) < desired_length:
            if prev_exhausted and next_exhausted:
                break
            ctx_iter += 1
            # add context before
            delta_idx = num_contexts_before - ctx_iter
            if result_index - delta_idx >= 0:
                prev = metas[result_index - delta_idx]
                # if same doc, extract text
                if prev.doc_path == meta.doc_path:
                    prev = prev.para
                    # only use if text differs from main text
                    if prev != text:
                        prev_ctx.append(prev)
                        total_text += prev
                else:
                    prev_exhausted = True
            # add context after
            delta_idx = num_contexts_before + ctx_iter
            if result_index + delta_idx < len(metas):
                next = metas[result_index + delta_idx]
                # if same doc, extract text
                if next.doc_path == meta.doc_path:
                    next = next.para
                    # only use if text differs from main text
                    if next != text:
                        next_ctx.append(next)
                        total_text += next
                else:
                    next_exhausted = True
        for prev in reversed(prev_ctx):
            output_tuples.append((context_on, prev, context_off))
        output_tuples.append((highlight_on, text, highlight_off))
        for next in next_ctx:
            output_tuples.append((context_on, next, context_off))
    else:
        for x in range(num_contexts_before):
            delta_idx = num_contexts_before - x
            if result_index - delta_idx >= 0:
                prev = metas[result_index - delta_idx]
                # if same doc, extract text
                if prev.doc_path == meta.doc_path:
                    prev = prev.para
                    # only use if text differs from main text
                    if prev != text:
                        output_tuples.append((context_on, prev, context_off))
        output_tuples.append((highlight_on, text, highlight_off))
        for x in range(num_contexts_after):
            delta_idx = x
            if result_index + delta_idx < len(metas):
                next = metas[result_index + delta_idx]
                # if same doc, extract text
                if next.doc_path == meta.doc_path:
                    next = next.para
                    # only use if text differs from main text
                    if next != text:
                        output_tuples.append((context_on, next, context_off))

    fmt_filn = '{filn:' + str(max_filn_len) + 's}'
    filn = fmt_filn.format(filn=filn)
    for prefix, text, postfix in output_tuples:
        wrap_prefix = f'#{result_number:02} ({distance:5.3f}): {filn} | '
        subsequent_indent = ' ' * (len(wrap_prefix) - 2) + '| '
        line = f'{wrap_prefix}{prefix}{text}{postfix}'
        wrapped_text = textwrap.fill(line, width=output_width, initial_indent='',
                                     subsequent_indent=subsequent_indent)
        print(f'{wrapped_text}')


def process_query(query_text, embedding_cache, faiss_index, metadata, k_results=20):
    print(f'\n=== Showing top {k_results} matches for >>>{query_text}<<< ===\n')
    query_embedding = get_query_embeddings(query_text, embedding_cache)
    query_embedding = normalize_embeddings(query_embedding)
    search_start_time = time.time()
    faiss_distances, faiss_indices = search_faiss_index(
            faiss_index, query_embedding, k=k_results)
    search_end_time = time.time()
    print(f"Search took {search_end_time-search_start_time:0.3f} seconds.")

    result_indices = faiss_indices[0]
    result_distances = faiss_distances[0]

    max_filn_len = 0
    for idx in result_indices:
        filn_len = len(os.path.basename(metadata[idx].doc_path))
        if filn_len > max_filn_len:
            max_filn_len = filn_len

    # get terminal width
    terminal_size = shutil.get_terminal_size()
    num_cols = terminal_size.columns

    # compact results: supress existing identical ones, regardless of doc
    result_texts = []
    for r_no, (idx, dist) in enumerate(zip(result_indices, result_distances)):
        text = metadata[idx].para
        if text in result_texts:
            continue
        result_texts.append(text)
        show_result(r_no, metadata, idx, dist,
                    max_filn_len=max_filn_len,
                    auto_contexts = True,
                    num_contexts_before=1,
                    num_contexts_after=1,
                    context_on='\033[90m',
                    context_off='\033[0m',
                    highlight_on='\033[34m',
                    highlight_off='\033[0m',
                    output_width=num_cols - 1,
                    )


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage  : python {sys.argv[0]} path/to/data num_results')
        print(f"Example: python {sys.argv[0]} ./data 20")
        sys.exit(1)

    directory = sys.argv[1]
    k_results = int(sys.argv[2])

    embedding_cache = EmbeddingCache()
    print(f'Embedding cache holds {len(embedding_cache.values)} unique texts')

    # Load or create metadata, embeddings, faiss index
    if os.path.exists(FILN_METADATA):
        metadata = load_metadata(FILN_METADATA)
        # we assume that embeddings cache is full if we have metadata
        faiss_index = load_faiss_index(FILN_FAISS_INDEX)
    else:
        metadata = read_text_files_by_paragraph(directory)

        # fill embeddings cache
        print('Packing batches...')
        metadata_batches = create_optimal_batches(metadata)
        print(f'Generating/loading embeddings for {len(metadata)} texts in {len(metadata_batches)} batches...')
        embedding_batches = get_openai_embeddings(metadata_batches, embedding_cache, just_load=False)

        # now flatten meta and embeddings into flat lists again
        # so they can be accessed by index returned by faiss search
        print('Re-organizing...')
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
        print('Saving embeddings...')
        embedding_cache.save_cache()
        save_metadata(metadata, FILN_METADATA)
        faiss_index = create_faiss_index(embeddings)
        save_faiss_index(faiss_index,FILN_FAISS_INDEX)

    while True:
        query = input("Enter your query (or type 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        process_query(query, embedding_cache, faiss_index, metadata, k_results=k_results)

