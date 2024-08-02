from tqdm import tqdm
import heapq


def create_optimal_batches(metas, max_size=8191):
    # Sort the list of tuples in descending order based on the number of tokens
    sorted_metas = sorted(metas, key=lambda x: x[2], reverse=True)

    # Priority queue to keep track of batches' current sizes
    heap = []
    batches = []

    for meta in tqdm(sorted_metas):
        placed = False
        tokens = meta[2]

        # Check if there's any batch that can accommodate the current tuple
        if heap and heap[0][0] + tokens <= max_size:
            # Get the batch with the smallest current size
            current_batch_size, batch_index = heapq.heappop(heap)
            batches[batch_index].append(meta)
            current_batch_size += tokens
            # Push the updated batch size back into the heap
            heapq.heappush(heap, (current_batch_size, batch_index))
            placed = True

        # If no suitable batch was found, create a new batch
        if not placed:
            batches.append([meta])
            # Push the new batch into the heap
            heapq.heappush(heap, (tokens, len(batches) - 1))

    return batches


# the orig algo, super slow
def create_optimal_batches_SLOW(metas, max_size):
    # Sort the list of tuples in descending order based on the number of tokens
    sorted_metas = sorted(metas, key=lambda x: x[2], reverse=True)
    
    batches = []
    
    print('Packing batches...')
    for meta in tqdm(sorted_metas):
        placed = False
        tokens = meta[2]
        # Try to place the item in one of the existing batches
        for batch in batches:
            current_batch_size = sum(meta[2] for meta in batch)
            if current_batch_size + tokens <= max_size:
                batch.append(meta)
        else:
            # If the item was not placed in any existing batch, create a new batch
            batches.append([meta])
    return batches

if __name__ == '__main__':
    import sys
    from textloading import read_text_files_by_paragraph
    metas = read_text_files_by_paragraph(sys.argv[1])
    max_size = 8191
    batches = create_optimal_batches(metas, max_size)
    print(len(batches))
    for b in batches[0:5]:
        bl = sum(m[2] for m in b)
        print(bl)
    print('...')
    for b in batches[-5:]:
        bl = sum(m[2] for m in b)
        print(bl)
