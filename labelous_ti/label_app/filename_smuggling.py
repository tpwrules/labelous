import re

# we have to somehow smuggle the current annotation ID and image ID through the
# tool. we do this by encoding the IDs in the filename.
filename_re = re.compile(r'^i([0-9]+|x)_a([0-9]+|x)$')
# the syntax is 'i' followed by the image ID, then 'a' followed by the
# annotation ID. if not necessary or not known, the ids can be 'x'. the caller
# can choose which parts are needed by the keyword args.
def decode_filename(filename, image_id=False, anno_id=False):
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

    return image_id, anno_id

# inverse of the above
def encode_filename(image_id=None, anno_id=None):
    return "i{}_a{}".format(
        "x" if image_id is None else int(image_id),
        "x" if anno_id is None else int(anno_id))
