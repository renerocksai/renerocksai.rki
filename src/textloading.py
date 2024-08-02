import os
from tqdm import tqdm
import tiktoken
import re

openai_encoding = tiktoken.get_encoding('cl100k_base')

space_re = re.compile(r' +')
newline_re = re.compile(r'\n+')
nbsp_re = re.compile(r'(&nbsp;)+')


def normalize_whitespace(text):
    # Replace multiple spaces with a single space
    text = space_re.sub(' ', text)
    text = newline_re.sub('\n', text)
    text = newline_re.sub('\n', text)
    text = nbsp_re.sub(' ', text)
    return text


def token_length(para):
    return len(openai_encoding.encode(para))


def get_token_lengths(metadata):
    print('Calculating token lengths... Program will exit after this.')
    token_lengths = []
    for index, meta in enumerate(metadata):
        current_length = meta[2]
        if current_length > 1000:
            if current_length > 8191:
                print('extremely', end=' ')
            print('big:', current_length, metadata[index][0])
        token_lengths.append(current_length)
    print(f'Max token length:', np.max(token_lengths))
    print(f'Total: {np.sum(token_lengths)} in {len(metadata)} texts.')
    print('Exiting voluntarily. Please comment out the line calling get_token_lengths().')
    sys.exit(1)
    return token_lengths


def textfile_to_paras(filn):
    with open(filn, 'rt', encoding='utf-8', errors='ignore') as f:
        lines = [l.strip() for l in f.readlines()]

    paras = []
    current_para = []
    for line in lines:
        if not line:
            paras.append(normalize_whitespace(' '.join(current_para)))
            current_para = []
        else:
            current_para.append(line)
    paras.append(normalize_whitespace(' '.join(current_para)))
    return paras


def read_text_files_by_paragraph(directory, extension='.txt'):
    """
    return metadata, where metadata is a tuple of filename,
    paragraph text, num_tokens, and kind. atm kind is always paragraph.
    """
    metadata = []  # To store the document, paragraph/table info, and the text
    print('Loading texts...')
    all_files = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            if filename.endswith(extension):
                doc_path = os.path.join(dirpath, filename)
                all_files.append(doc_path)
    for doc_path in tqdm(sorted(all_files)):
        # print('Processing', doc_path)
        # Extract paragraphs
        for para in textfile_to_paras(doc_path):
            para = para.strip()
            if para:  # Ensure that the text is not empty
                metadata.append((doc_path, para, token_length(para), "paragraph"))
    return metadata

