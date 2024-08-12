"""
Convert existing .txt files that are e.g. the result of pdftotext

Use langchain TextSplitter.

Convert paragraphs with overlaps.

Replace .txt files and keep a copy of the original in .bak files 
"""

import sys
import os
from tqdm import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter


supported_extensions=['.txt']

separators=[ "\n\n", "\n", ".", "!", "?", ",", " ", ]


def len_func(text):
    return len(text)


text_splitter = RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=600,
        chunk_overlap=200,
        length_function=len_func,
)


def convert_file(filn):
    basename = os.path.basename(filn)
    if basename.startswith('.'):
        return None
    root, extension = os.path.splitext(filn)
    extension = extension.lower()
    output_file = filn + '.txt'
    ret = 0

    if extension not in supported_extensions:
        print(filn)
        raise RuntimeError("unreachable")

    # create a backup file so we can revert
    bak_file = filn + '.bak'
    if os.path.exists(bak_file):
        os.system(f"cp '{bak_file}' '{filn}'")
    with open(filn, 'rt', errors='ignore') as f:
        try:
            text = f.read()
        except:
            print()
            print()
            print('ERROR IN FILE', filn)
            raise RuntimeError()

    text = text.replace('\n', ' ')
    with open(bak_file, 'wt') as bak:
        bak.write(text)

    # we don't care about metadata for now
    docs = text_splitter.create_documents([text])
    with open(filn, 'wt') as f:
        for doc in docs:
            f.write(f'{doc.page_content}\n\n')
    return ret


def get_files(directory):
    all_files = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            basename = os.path.basename(filename)
            if basename.startswith('.') or basename.startswith('~'):
                continue
            extension = os.path.splitext(filename)[1].lower()
            if (extension not in supported_extensions):
                continue
            doc_path = os.path.join(dirpath, filename)
            all_files.append(doc_path)
    all_files.sort()
    return all_files


def process_folder(directory, error_files):
    all_files = get_files(directory)
    print(f'Converting {len(all_files)} files in {directory}...')
    for f in tqdm(all_files):
        ok = convert_file(f)
        if ok != 0:
            error_files.append(f)
    return error_files

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} data_dir')
        sys.exit(1)
    error_files = []
    directory = sys.argv[1]
    error_files = process_folder(directory, [])
    if error_files:
        print('The following files had errors or warnings:')
        print('\n'.join(error_files))
    print("READY.")

