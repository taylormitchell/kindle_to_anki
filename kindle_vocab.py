import json 
import urllib.request 
import requests
import re
import sqlite3
import datetime
import shutil
from oxfdict import APP_ID, APP_KEY 

class NotInDictError(Exception):
    pass

# Anki

def _create_request_dict(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def _invoke(action, **params):
    requestDict = _create_request_dict(action, **params)
    requestJson = json.dumps(requestDict).encode('utf-8')
    request = urllib.request.Request('http://localhost:8765', requestJson)
    response = json.load(urllib.request.urlopen(request))
    return response['result']


def add_note(anki_dict):
    return _invoke("addNote", note=anki_dict)


def note_exists(word):
    res = _invoke('findNotes', query=f"Word:{word}")
    if res:
        return True
    return False


def get_note_id(word):
    res = _invoke('findNotes', query=f"Word:{word}")
    if res:
        return res[0]
    return None


def update_note(anki_dict, note_id=None):
    note_id = note_id or get_note_id(anki_dict)
    note = {"id":note_id, "fields": anki_dict["fields"]}
    return _invoke("updateNoteFields", note=note)

# Kindle

def get_latest_kindle_lookups():
    # Get timestamp of last synced lookup
    conn = sqlite3.connect(path_vocab_old)
    cursor = conn.cursor()
    try:
        cursor.execute("select max(timestamp) from lookups")
        record = cursor.fetchone()
    finally:
        cursor.close()
    max_timestamp = record[0]

    # Get lookups since last sync 
    conn = sqlite3.connect(path_vocab)
    cursor = conn.cursor()
    try:
        cmd = f"""
        select w.word, w.stem, w.timestamp, lu.usage, bi.title 
        from words w 
        left join lookups lu on w.id = lu.word_key
        left join book_info bi on bi.id = lu.book_key
        where lu.timestamp > {max_timestamp}"""
        cursor.execute(cmd)
        records = cursor.fetchall()
        columns = [t[0] for t in cursor.description]
        records = [{c:v for c,v in zip(columns, record)} for record in records]
    finally:
        cursor.close()

    lookups = []
    for record in records:
        example = re.sub("^\s*|\s*$", "", record["usage"])
        lookup = {
            "word": record["word"],
            "usages": [
                {"text": record["usage"], "source": record["title"]}
            ]
        }
        lookups.append(lookup)

    return lookups


# Kindle to Anki

def examples_to_field(examples, word):
    field = ""
    for example in examples:
        text = re.sub(f"({word})", f"<span class='word'>\g<1></span>", example['text'], flags=re.IGNORECASE)
        text = f"<span class='example'>{text}</span>"
        source = example.get("source")
        if source:
            text += f"<span class='source'>{source}</span>"
        field += f"<li>{text}</li>"
    field = f"<ul>{field}</ul>"

    return field


def create_anki_dict(word, definition, examples, deck="Default", model="Vocab"):
    return {
        "deckName": deck,
        "modelName": model,
        "fields": {
            "Word": word,
            "Definition": definition,
            "Examples": examples_to_field(examples, word)}
        } 
        

# Oxford

def call_oxford_dict(word, language="en-gb"):
    source = "oxford dictionary"
    url = "https://od-api.oxforddictionaries.com:443/api/v2/entries/" + language + "/" + word.lower()
    r = requests.get(url, headers={"app_id": APP_ID, "app_key": APP_KEY})
    res = r.json()
    try:
        sense = res["results"][0]["lexicalEntries"][0]["entries"][0]["senses"][0]
        definition = sense["shortDefinitions"][0]
    except KeyError:
        raise NotInDictError

    examples = [{"text": ex["text"], "source": source} for ex in sense.get("examples",[])]

    return definition, examples


if __name__=="__main__":
    path_vocab_old = "vocab.db"
    path_vocab = "/Volumes/Kindle/system/vocabulary/vocab.db"
    deck = "Default"

    # main
    for kindle_lookup in get_latest_kindle_lookups():
        word, kindle_usages = kindle_lookup["word"], kindle_lookup["usages"]
        print(word)
        try:
            definition, oxf_examples = call_oxford_dict(word)
        except NotInDictError:
            print(f"^ skipped")
            continue
        examples = kindle_usages[:1] + oxf_examples[:1]
        anki_dict = create_anki_dict(kindle_lookup["word"], definition, examples, deck=deck)
        # Upload to anki
        note_id = get_note_id(word)
        if not note_id:
            add_note(anki_dict)
        else:
            update_note(anki_dict, note_id)
    # Replace the old vocab file with the new one
    shutil.copyfile(path_vocab, path_vocab_old)
