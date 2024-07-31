# renerocks.rki

## [FAISS](https://github.com/facebookresearch/faiss)-Powered Semantische Suche über die RKI-Protokolle

Dies ist ein Ad-Hoc-Forschungsprojekt zum Testen des Ansatzes, FAISS für
semantische Suche in deutschen Texten zu verwenden.

## ACHTUNG: Alpha-Software: momentan eher nur für Bastler und Interessierte geeignet

Eckdaten:

- OpenAI Embeddings (model=text-embedding-3-large)
- FAISS Index Search (Cosine Distance Similarity Search)

Dieses Tool benötigt:

- einen API-Key von OpenAI
- das Tool `pandoc` zum Konvertieren der Word DOCX Dateien ins RST-Format
- python3 und ein paar Pakete

## Wofür ein OpenAI-API-Key?

- Initial müssen alle Texte in Embeddings konvertiert werden (ca. 10h)
- Jede Suchanfrage muss in Embeddings umgewandelt werden
    - allerdings werden die Embeddings gecached
    - jede erneute Suchanfrage im exakt gleichen Wortlaut erfordert keine
      weitere Konvertierung.
- Preis für Embeddings: $0.13 / 1M tokens
    - wir haben 88 009 Paragraphen mit einem Mean von 39 Tokens pro Paragraphen
    - macht ca. 3.5Mio Tokens insgesamt
    - macht ca. 0.5 USD insgesamt


## Quickstart

```shell
# EINMALIG: download into ./data Sitzungsprotokolle_orig_docx.zip
$ cd data
$ unzip Sitzungsprotokolle_orig_docx.zip

# EINMALIG: Texte ins RST-Format konvertieren
$ ./generate_txt.sh
$ cd ..

# Bei OpenAI einen API-Key besorgen.
$ export OPENAI_RKI_KEY=xxxxx-xxxxx-xxxxx-xxx

# EINMALIG: Optional: Python-Env anlegen
$ python3 -m venv env
$ source env/bin/activate # on macos

# EINMALIG: Python-Pakete installieren
$ pip install -f requirements.txt

# Suchanfrage starten
$ python main.py "Suchanfrage"
```

Beim ersten Start werden erstmal die Embeddings von OpenAI "abgeholt". Das
dauert ca. 10h.

Danach muss ein [FAISS](https://github.com/facebookresearch/faiss)-Index für die
Suche aus allen Embeddings gebildet werden. Das dauert ??? auch ein bisschen, je
nach CPU. Findige Programmierer mit NVIDIA-GPU können den Code anpassen, um die
GPU-Variante von FAISS zu benutzen. Die muss um einiges schneller sein.

Wenn der Index einmal berechnet wurde, wird er gespeichert und beim nächsten
Programmstart neu geladen. Er muss dann nicht nochmal berechnet werden.
