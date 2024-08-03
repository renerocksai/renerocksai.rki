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
from myargs import parse_args


FILN_FAISS_INDEX = 'faiss.index'
FILN_METADATA = 'metadata.pkl'


def get_query_embeddings(text, embedding_cache):
    embedding = embedding_cache.get(text, auto_save=False)   # TODO: auto_saving takes too long if big
    return np.array([embedding])

# by normalizing, we effectively perform a cosine search. see faiss github
def normalize_embeddings(embeddings):
    print('Normalizing embeddings...')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized_embeddings = embeddings / norms
    return normalized_embeddings

def search_faiss_index(index, query_embedding, k=5):
    distances, indices = index.search(query_embedding, k)
    return distances, indices

def load_faiss_index(filepath):
    print('Loading FAISS index...')
    return faiss.read_index(filepath)

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
    query_text = f'\033[31m{query_text}\033[0m'
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
        print()
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
    args, kwargs, flags = parse_args(sys.argv[1:])
    if len(args) != 2:
        print(f'Usage  : python {sys.argv[0]} dataset_name num_results')
        print(f"Example: python {sys.argv[0]} sitzungsprotokolle 20")
        sys.exit(1)

    dataset_name = args[0]
    k_results = int(args[1])
    dataset_dir = kwargs.get('dataset_dir', '.')

    # TODO: use a different embedding cache for queries
    query_embedding_cache = EmbeddingCache('queries', dataset_dir=dataset_dir)
    print(f'Query Embedding cache holds {len(query_embedding_cache.values)} unique texts')

    filn_metadata = os.path.join(dataset_dir, f'{dataset_name}_{FILN_METADATA}')
    filn_faiss = os.path.join(dataset_dir, f'{dataset_name}_{FILN_FAISS_INDEX}')

    # Load metadata, faiss index
    if os.path.exists(filn_metadata):
        metadata = load_metadata(filn_metadata)
        # we assume that embeddings cache is full if we have metadata
        faiss_index = load_faiss_index(filn_faiss)
    else:
        print('Dataset not found')
        sys.exit(1)

    while True:
        query = input("Enter your query (or type 'exit' to quit): ")
        if query.lower() == 'exit':
            break
        process_query(query, query_embedding_cache, faiss_index, metadata, k_results=k_results)

