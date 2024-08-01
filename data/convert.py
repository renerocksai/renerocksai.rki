import sys
import os
from tqdm import tqdm
import email
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage

supported_extensions = [
  ".pdf", ".html", ".rtf", ".odt", ".msg",
]

libreoffice_extensions = [
        ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
]


grep = 'grep'
libreoffice = 'libreoffice'

import platform
if platform.system() == 'Darwin':
    grep = 'ggrep'
    libreoffice = '/Applications/LibreOffice.app/Contents/MacOS/soffice'

def get_files(directory):
    all_files = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            basename = os.path.basename(filename)
            if basename.startswith('.') or basename.startswith('~'):
                continue
            extension = os.path.splitext(filename)[1].lower()
            if (extension not in supported_extensions) and (extension not in libreoffice_extensions):
                continue
            doc_path = os.path.join(dirpath, filename)
            all_files.append(doc_path)
    all_files.sort()
    return all_files


def save_attachments_and_strip_email(raw_email, output_file):
    # Parse the raw email
    with open(raw_email, 'rb') as f:
        raw_content = f.read()
        msg = BytesParser(policy=policy.default).parsebytes(raw_content)


    attachments = []
    attachments_folder = raw_email + '.attachments'

    # Create a new email message to store the parts without attachments
    stripped_msg = EmailMessage()

    # Copy headers from the original message
    for header, value in msg.items():
        stripped_msg[header] = value

    def process_part(part):
        content_disposition = part.get("Content-Disposition", None)
        content_type = part.get_content_type()
        
        if part.is_multipart():
            # Create a new multipart message
            new_msg = EmailMessage()
            new_msg.set_type(part.get_content_type())
            for sub_part in part.iter_parts():
                sub_result = process_part(sub_part)
                if sub_result:
                    new_msg.attach(sub_result)
            return new_msg
        elif content_disposition and ("attachment" in content_disposition or "inline" in content_disposition and content_type not in ['text/plain']):
            filename = part.get_filename()
            if not filename:
                # Generate a filename for inline attachments if not present
                ext = part.get_content_subtype()
                filename = f"inline_attachment_{len(attachments) + 1}.{ext}"
            
            # Ensure the filename is safe
            safe_filename = filename.replace(" ", "_")
            filepath = os.path.join(attachments_folder, safe_filename)
            payload = part.get_payload(decode=True)
            if payload is not None:
                os.makedirs(attachments_folder, exist_ok=True)
                with open(filepath, "wb") as f:
                    f.write(payload)
                attachments.append(filepath)
            return None
        else:
            return part

    # Process each part of the message
    if msg.is_multipart():
        for part in msg.iter_parts():
            if part is None:
                continue
            result = process_part(part)

            if result:
                try:
                    can_error = str(result)
                    stripped_msg.attach(result)
                except:
                    pass
    else:
        # If the message is not multipart, just copy it as is
        stripped_msg.set_content(msg.get_content())

    with open(output_file, 'wb') as f:
        f.write(stripped_msg.as_bytes())
    return attachments


def convert_file(filn):
    basename = os.path.basename(filn)
    if basename.startswith('.'):
        return None
    root, extension = os.path.splitext(filn)
    extension = extension.lower()
    output_file = filn + '.txt'
    attachments = []
    ret = 1

    if extension in supported_extensions:
        if extension in ['.html', '.odt']:
            ret = os.system(f'pandoc "{filn}" -t txt --list-tables -o "{output_file}"')
        elif extension == '.pdf':
            ret = os.system(f'pdftotext "{filn}" "{output_file}"')
        elif extension == '.rtf':
            ret = os.system(f'unrtf --text "{filn}" > "{output_file}"')
        elif extension in ['.ppt', '.pptx']:
            # not sure ppt can be treated like pptx
            ret = os.system(f'unzip -qc "{filn}" ppt/slides/slide*.xml | {grep} -oP \'(?<=<a:t>).*?(?=</a:t>)\' >"{output_file}"')
        elif extension == '.msg':
            raw_file = filn + '.raw'
            ret = os.system(f'msgconvert --outfile "{raw_file}" "{filn}"')
            attachments = save_attachments_and_strip_email(raw_file, output_file)
        else:
            print(f)
            raise RuntimeError("unreachable")
    elif extension in libreoffice_extensions:
        pdf_file = os.path.splitext(filn)[0] + '.pdf'
        if os.path.exists(pdf_file):
            # we've converted it already in a previous run
            ret = 0
        else:
            pdf_dir = os.path.dirname(filn)
            ret = os.system(f'{libreoffice} --headless --convert-to pdf "{filn}" --outdir "{pdf_dir}"') 
            if not os.path.exists(pdf_file):
                # linux version may create .docx.pdf
                if os.path.exists(filn + '.pdf'):
                    ret = os.system(f'mv "{filn + ".pdf"}" "{pdf_file}"')
                else:
                    print(f'Cannot find converted PDF file for {filn}')
                    print(f'Expected {pdf_file}')
                    ret = 1

        if ret == 0:
            return convert_file(pdf_file)
        else:
            print(f'Could not convert to PDF: {filn}')
    return ret, attachments

def process_folder(directory, all_attachments, error_files):
    all_files = get_files(directory)
    print(f'Converting {len(all_files)} files in {directory}...')
    for f in tqdm(all_files):
        ok, attachments = convert_file(f)
        if ok != 0:
            error_files.append(f)
        if attachments:
            all_attachments.extend(attachments)
    return all_attachments, error_files

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python {sys.argv[0]} data_dir')
        sys.exit(1)
    all_attachments = []
    error_files = []
    directory = sys.argv[1]

    all_attachments, error_files = process_folder(directory, [], [])
    while True:
        new_attachment_folders = set()
        for att in all_attachments:
            new_attachment_folders.add(os.path.dirname(att))
        all_attachments = []
        for folder in new_attachment_folders:
            attachments, error_files = process_folder(folder, [], error_files)
            all_attachments.extend(attachments)
        if not all_attachments:
            break

    print('The following files had errors or warnings:')
    print('\n'.join(error_files))
