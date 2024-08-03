from tqdm import tqdm
import heapq


def create_optimal_batches(metas, max_tokens=8191, max_batch_size=2000):
    # Sort the list of tuples in descending order based on the number of tokens
    sorted_metas = sorted(metas, key=lambda x: x.token_length, reverse=True)

    # Priority queue to keep track of batches' current sizes
    heap = []
    batches = []

    num_skipped = 0

    for meta in tqdm(sorted_metas):
        placed = False
        tokens = meta.token_length

        # Check if there's any batch that can accommodate the current tuple
        if heap and heap[0][0] + tokens <= max_tokens:
            # Get the batch with the smallest current size
            current_batch_size, batch_index = heapq.heappop(heap)
            if len(batches[batch_index]) < max_batch_size:
                batches[batch_index].append(meta)
                current_batch_size += tokens
                # Push the updated batch size back into the heap
                heapq.heappush(heap, (current_batch_size, batch_index))
                placed = True

        # If no suitable batch was found, create a new batch
        if not placed:
            if meta.token_length >= max_tokens:
                # raise ValueError("Batch too large", meta.doc_path, meta.token_length)
                # heml inline images
                num_skipped += 1
                continue
            batches.append([meta])
            # Push the new batch into the heap
            heapq.heappush(heap, (tokens, len(batches) - 1))
    if num_skipped:
        print('Skipped too long paras', num_skipped)
    return batches


if __name__ == '__main__':
    import sys
    from textloading import read_text_files_by_paragraph
    metas = read_text_files_by_paragraph(sys.argv[1])
    max_tokens = 8191
    batches = create_optimal_batches(metas, max_tokens=max_tokens)
    print(len(batches))
    for b in batches[0:5]:
        bl = sum(m.token_length for m in b)
        print(bl, len(b))
    print('...')
    for b in batches[-5:]:
        bl = sum(m.token_length for m in b)
        print(bl, len(b))

    tokens = [meta.token_length for meta in metas]


    print(f'{sum(tokens)} total tokens in {len(metas)} paras')
