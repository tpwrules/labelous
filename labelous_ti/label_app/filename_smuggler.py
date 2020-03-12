# we have to get  several pieces of information into the tool and back out to us
# when it accesses its api. unfortunately the only thing it takes is a filename,
# and the only thing it gives back to us is a filename. naturally, we then
# encode all the stuff that's important to us into the filename.

import collections
import re

__all__ = ["encode_filename", "decode_filename", "NameData"]

NameData = collections.namedtuple("NameData",
    field_names=["image_id", "anno_id"],
    defaults=[None, None])

filename_re = re.compile(r'^i([0-9]+|x)_a([0-9]+|x)$')

def decode_filename(filename, image_id=False, anno_id=False):
    if filename[-4:] in (".jpg", ".svg", ".xml"):
        filename = filename[:-4]
    
    match = filename_re.match(filename)
    if match is None:
        raise ValueError("invalid filename: {}".format(filename))

    if match.group(1) == "x":
        if image_id is True:
            raise ValueError("image ID required, but not provided")
        else:
            image_id = None
    else:
        image_id = int(match.group(1))

    if match.group(2) == "x":
        if anno_id is True:
            raise ValueError("anno ID required, but not provided")
        else:
            anno_id = None
    else:
        anno_id = int(match.group(2))

    return NameData(image_id=image_id, anno_id=anno_id)

# inverse of the above
def encode_filename(**kwargs):
    nd = NameData(**kwargs)
    return "i{}_a{}".format(
        "x" if nd.image_id is None else int(nd.image_id),
        "x" if nd.anno_id is None else int(nd.anno_id),
    )
