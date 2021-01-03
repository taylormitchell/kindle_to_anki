import json
import urllib.request 

class DuplicateError(Exception):
    def __init__(self, message=""):
        self.message = message

def _create_request_dict(action, **params):
    return {'action': action, 'params': params, 'version': 6}


def _invoke(action, **params):
    requestDict = _create_request_dict(action, **params)
    requestJson = json.dumps(requestDict).encode('utf-8')
    request = urllib.request.Request('http://localhost:8765', requestJson)
    response = json.load(urllib.request.urlopen(request))
    return response


def add_note(deck, model, fields):
    anki_dict = {
        "deckName": deck,
        "modelName": model,
        "fields": fields
        } 
    response = _invoke("addNote", note=anki_dict)
    error = response.get("error")
    if not error:
        return response["result"]
    if error == "cannot create note because it is a duplicate":
        raise DuplicateError(error)
    else:
        raise ValueError(error) 


def get_note_id(word):
    res = _invoke('findNotes', query=f"Word:{word}")
    if res:
        return res[0]
    return None