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
        passage = lines[3]

        m = re.search("page (\d+)", lines[1])
        page = m.groups()[0] if m else UNKNOWN

        m = re.search("Location (\d+-\d+)", lines[1])
        loc = m.groups()[0] if m else UNKNOWN

        date = UNKNOWN
        m = re.search("Added on (.*)\s*", lines[1])
        if m:
            date = datetime.datetime.strptime(m.groups()[0], "%A, %B %d, %Y %I:%M:%S %p")
            timestamp = int(date.timestamp())
            
        return Clipping(title, passage, page, loc, timestamp)
        
    @classmethod
    def from_filepath(cls, filepath):
        with open(filepath) as f:
            clip_strs = f.read().split("==========\n")[:-1]
        clippings = [cls.parse_clip_str(clip_str) for clip_str in clip_strs]
        return cls(clippings)
    
    def latest_clipping(self):
        return max([c.added_on for c in self])
        
        
class Clipping:
    def __init__(self, title, passage, page, location, added_on):
        self.title = title
        self.passage = passage
        self.page = page
        self.location = location
        self.added_on = added_on


def clipping_to_anki_fields(clipping):
    fields = {k:str(v) for k,v in clipping.__dict__.items()}
    fields["passage_and_title"] = clipping.passage + clipping.title
    return fields
        

if __name__=="__main__":

    filepath_old = "My Clippings.txt"
    filepath_new = "/Volumes/Kindle/documents/My Clippings.txt"
    deck = "Review only"
    model = "Kindle Highlight"

    my_clippings_old = MyClippings.from_filepath(filepath_old)
    my_clippings = MyClippings.from_filepath(filepath_new)

    last_clipping_ankified = my_clippings_old.latest_clipping()
    for clipping in my_clippings:
        if clipping.added_on > last_clipping_ankified:
            print(f"Adding '{clipping.passage}'")
            try:
                res = anki.add_note(deck, model, fields=clipping_to_anki_fields(clipping))
            except anki.DuplicateError as e:
                print(e)

    shutil.copyfile(filepath_new, filepath_old)
