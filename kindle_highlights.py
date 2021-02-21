import re
import datetime
import anki
import shutil

UNKNOWN = "unknown"

class MyClippings(list):
    def __init__(self, clippings):
        for clip in clippings:
            self.append(clip)
        
    @staticmethod
    def parse_clip_str(clip_str):
        lines = clip_str.split("\n")

        title = lines[0]

        m = re.search("Your (\w+)", lines[1])
        type = m.groups()[0]
        if type == "Highlight":
            quote = lines[3]
            note = ""
        else:
            quote = ""
            note = lines[3]

        m = re.search("page (\d+)", lines[1])
        page = m.groups()[0] if m else UNKNOWN

        m = re.search("Location ([\d-]+)", lines[1])
        loc = m.groups()[0] if m else UNKNOWN

        date = UNKNOWN
        m = re.search("Added on (.*)\s*", lines[1])
        if m:
            date = datetime.datetime.strptime(m.groups()[0], "%A, %B %d, %Y %I:%M:%S %p")
            timestamp = int(date.timestamp())
            
        return Clipping(title, quote, note, page, loc, timestamp)
        
    @classmethod
    def from_filepath(cls, filepath):
        with open(filepath) as f:
            clip_strs = f.read().split("==========\n")[:-1]
        clippings = [cls.parse_clip_str(clip_str) for clip_str in clip_strs]
        return cls(clippings)
    
    def latest_clipping(self):
        return max([c.added_on for c in self])
        
        
class Clipping:
    def __init__(self, title, quote, note, page, location, added_on):
        self.title = title
        self.quote = quote
        self.note = note
        self.page = page
        self.location = location
        self.added_on = added_on


def is_pair(highlight, note):
    highlight_loc_end = highlight.location.split("-")[-1]
    return (highlight.title==note.title) and (highlight_loc_end == note.location)


def consolidate(clippings):
    clips_consolidated = []
    i = 0
    while i < (len(clippings)-1):
        clip, next_clip = clippings[i], clippings[i+1]
        if next_clip.note and is_pair(clip, next_clip):
            clip.note = next_clip.note
            i += 1
        clips_consolidated.append(clip)
        i += 1
    return clips_consolidated


#def clipping_to_anki_fields(clipping):
#    fields = {k:str(v) for k,v in clipping.__dict__.items()}
#    fields["passage_and_title"] = clipping.passage + clipping.title
#    return fields
        

def add_clipping(clipping, deck):
    if clipping.quote:
        fields = {k:str(v) for k,v in clipping.__dict__.items()}
        fields["quote_and_title"] = clipping.quote + clipping.title
        model = "Kindle Highlight"
    else:
        fields = {k:str(v) for k,v in clipping.__dict__.items()}
        fields["note_and_title"] = clipping.note + clipping.title
        model = "Kindle Note"
    try:
        anki.add_note(deck, model, fields=fields)
    except anki.DuplicateError as e:
        print(e)


if __name__=="__main__":

    filepath_old = "My Clippings.txt"
    filepath_new = "/Volumes/Kindle/documents/My Clippings.txt"
    deck = "Review only"
    model = "Kindle Highlight"

    my_clippings_old = MyClippings.from_filepath(filepath_old)
    my_clippings = MyClippings.from_filepath(filepath_new)

    last_clipping_ankified = my_clippings_old.latest_clipping()
    clips_to_add = [clip for clip in my_clippings if clip.added_on > last_clipping_ankified]
    clips_to_add = consolidate(clips_to_add)
    for clipping in clips_to_add:
        print(f"Adding '{clipping.quote or clipping.note}'")
        add_clipping(clipping, deck=deck)

    shutil.copyfile(filepath_new, filepath_old)
