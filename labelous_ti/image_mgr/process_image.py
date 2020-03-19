# this file handles the whole image processing deal, from image data through
# disk storage, thumbnail generation, and database update.

from django.db import IntegrityError, transaction
from django.conf import settings

import hashlib
import subprocess
import re
import io

import PIL.Image
import piexif

from .models import Image, THUMBNAIL_SIZE

# maximum size of JPEG, before processing, that we bother with
MAX_IMAGE_SIZE = 10*1024*1024 # 10MiB

# SECURITY CONCERNS

# Unfortunately, in this computer-generated nightmarescape, no data is
# trustworthy and all software is exploitable. Particularly, it seems, image
# processing libraries. Even if an image doesn't install a virus while being
# processed, serving it over the web is still dangerous, because it may be
# interpreted as a virus in certain circumstances. In light of all this, we take
# special security measures to hopefully mitigate these problems.

# Regarding image processor vulnerabilities, it seems many cases come from
# poorly-tested and excessively flexible image formats. To mitigate this
# concern, we accept only JPEG files. However, part of the problem is accurately
# identifying a particular file as JPEG, as the processor may have a different
# criterion. But this is all well-known stuff, and at least we're not using
# ImageMagick...

# The web allows the extra special category of skullduggery: polyglot files. 
# For example, this (http://lcamtuf.coredump.cx/squirrel/) image is a completely
# valid JPEG that's also completely valid HTML page. If an attacker can upload
# such an image to our site and get a user to load it (i.e. just send them a
# link), then the page can run Javascript with full access to cookies and
# requests, and then steal all the user's secrets, including those from the main
# domain! Even if it's not valid HTML, it could be e.g. a valid EXE, which would
# let an attacker host viruses that would be traced back to us. Browsers can be
# nosy, and things like file extensions and MIME types and nosniff headers won't
# always prevent the file from being reinterpreted and stop this type of attack.

# We solve both of these problems with the jpegtran tool from MozJPEG. It can
# only process JPEGs, so there's no way it can be vulnerable to a TIFF or MNG or
# PhotoCD or what have you attack. Hopefully then, it's well-tested against
# malicious JPEGs and can deal with them safely, and so we can avoid the first
# problem.

# We can almost entirely solve the second problem with jpegtran's party piece:
# optimization. To losslessly reduce the image's filesize, jpegtran completely
# parses the input JPEG, discards all the metadata and comments and stuff,
# reorganizes the macroblocks, generates optimal Huffman tables, and writes out
# a completely new file. Theoretically, polyglots won't survive the process. An
# attacker could model jpegtran's actions and design a polyglot that would sneak
# through, but I'm not sure it's possible. Rosetta Flash-style attacks are
# stopped because the Huffman tables get rebuilt. All the comments and EXIF data
# are deleted (which also helps preserve the uploader's privacy), so nothing can
# hide there. The only remaining option is to generate an image whose encoded
# data looks like another file. But would it look like anything when decoded?
# The administrator might see an image that looks like garbage and discard it
# before it has a chance to do any damage.

# All that said, I'd like to see a try!

# MEMORY AND PROCESSING TIME

# For this application, input images are limited to a 10MiB filesize. This will
# let users upload a wide variety of images and ensure the original quality is
# preserved. But processing them can be costly.

# To simplify the code and eliminate disk storage related problems, image data
# is always stored in memory until it's finally written to disk; there are no
# temporary files. But this means there can be four or five copies of the image
# floating around in memory during various stages of processing, hogging 40 or
# 50MiB. This doesn't count the several hundred MiB that might be used during
# jpegtran optimization or thumbnail generation.

# jpegtran's optimization process is slow and uses lots of memory. For a 10MiB
# image that needs to be transformed, it takes about 2 seconds and at most
# 512MiB of memory on my machine, but mine is pretty fast. However, jpegtran
# will be killed if it takes longer than 5 seconds to prevent truly ridiculous
# time wastage.

# It's probably not hard to DoS the system through image uploads if each image
# ties up the web server for several seconds and several hundred MiB of memory.
# We will accept that possibility here because we don't expect especially
# frequent image uploads, and any offenders could be easily identified and have
# their accounts disabled. But keep this problem in mind for other situations.
# It may be appropriate to reduce maximum file size, processing time, and memory
# usage thresholds.


# thrown when something goes wrong during processing
class ProcessingFailure(Exception):
    pass

# read EXIF orientation from the image. orientation test images are available at
# https://github.com/recurser/exif-orientation-examples
def get_exif_orientation(data):
    # we use piexif to process the original, potentially evil, image data.
    # theoretically this is safer because piexif is a pure python library and so
    # not vulnerable to buffer overflows and things.
    try:
        exif = piexif.load(data)
    except piexif.InvalidImageDataError as e:
        raise ProcessingFailure("piexif couldn't parse JPEG") from e

    try:
        orientation = exif["0th"][piexif.ImageIFD.Orientation]
    except KeyError:
        orientation = None # image didn't have an orientation tag

    # reset invalid orientation values
    if type(orientation) is not int or orientation < 2 or orientation > 8:
        orientation = 1 # to 1 -> image is oriented correctly

    return orientation


def jpegtran(in_data, orientation):
    # convert the orientation number to jpegtran command.
    # from http://sylvana.net/jpegcrop/exif_orientation.html

    # edge blocks can't be transformed quite right in all cases, so -trim simply
    # throws them away. we won't weep for the up to 15 columns or rows of pixels
    # that might be lost as a result.
    if orientation == 1:
        xform = ()
    elif orientation == 2:
        xform = ('-flip', 'horizontal', '-trim')
    elif orientation == 3:
        xform = ('-rotate', '180', '-trim')
    elif orientation == 4:
        xform = ('-flip', 'vertical', '-trim')
    elif orientation == 5:
        xform = ('-transpose', '-trim')
    elif orientation == 6:
        xform = ('-rotate', '90', '-trim')
    elif orientation == 7:
        xform = ('-transverse', '-trim')
    elif orientation == 8:
        xform = ('-rotate', '270', '-trim')
    else:
        raise ValueError("unknown orientation {}".format(orientation))

    args = [settings.L_JPEGTRAN_PATH,
        '-copy', 'none', # don't copy any metadata from input to output
        '-optimize', # build and recompress with optimal Huffman tables
        '-progressive', # reorder macroblocks in progressive scan to reduce size
                        # and improve download experience
        '-fastcrush', # don't bother optimizing progressive scan order; twice as
                      # fast to process and like 1% size difference
        '-maxmemory', '512m', # limit to 512MB of memory during processing;
                              # enough for transforming a 10MB image
        *xform, # transform image to correct EXIF orientation
        # data is passed through stdin and stdout so no files are specified
    ]

    try:
        result = subprocess.run(args,
            input=in_data, # pipe image data into jpegtran
            capture_output=True, # retrive image data piped out of jpegtran
            check=True, # throw exception if jpegtran didn't return success
            timeout=5, # kill jpegtran if it doesn't finish after 5 seconds in
                       # case it gets stuck or is doing evil things
        )
    except subprocess.CalledProcessError as e:
        # return code was nonzero
        raise ProcessingFailure("jpegtran didn't return success") from e
    except subprocess.TimeoutExpored as e:
        raise ProcessingFailure("jpegtran took too long") from e

    out_data = result.stdout
    if len(out_data) > MAX_IMAGE_SIZE:
        # shouldn't ever happen, but maybe jpegtran got stuck in a loop and
        # spewed garbage or something
        raise ProcessingFailure("jpegtran result too big")

    if len(out_data) < 2 or out_data[:2] != b"\xff\xd8":
        # make sure jpegtran gave back a JPEG. it should have if it said it
        # succeeded, but maybe it lied and printed an error message instead.
        # this also shouldn't ever happen.
        raise ProcessingFailure("jpegtran didn't return a JPEG")

    return out_data


# use PIL to make a thumbnail according to the various settings. must not be
# passed evil image data! returns (orig_size, thumb_data, thumb_size)
def make_thumbnail(image_data):
    image_file = io.BytesIO(image_data)
    thumb_file = io.BytesIO()

    thumb = PIL.Image.open(image_file)
    orig_size = thumb.size
    thumb.thumbnail(THUMBNAIL_SIZE)
    thumb.save(thumb_file, format="JPEG", quality=75)

    thumb_data = bytes(thumb_file.getbuffer())
    image_file.close()
    thumb_file.close()

    return (orig_size, thumb_data, thumb.size)


# returns True if an image is new, False if it's already in the database
# (ignoring whether or not it was ever processed), or raises an exception if it
# could not be processed
def process_image(uploader, name, orig_data):
    # perofrm basic sanity and validity checks

    # re-check size since this function may not have been called from the view
    if len(orig_data) > MAX_IMAGE_SIZE:
        raise ProcessingFailure("image too big")
    # make sure the file starts like a JPEG
    if len(orig_data) < 2 or orig_data[:2] != b"\xff\xd8":
        raise ProcessingFailure("missing JPEG SOI")

    # compute the SHA-256 of the image data so we can deduplicate images
    image_hash = hashlib.sha256(orig_data).digest()
    
    # make a hidden image record with the given hash. we expect images to be
    # unique, so we try and create it first.
    try:
        image = Image(file_path='', uploader=uploader,
            available=False, deleted=True, uploaded=False,
            original_hash=image_hash,
            image_x=0, image_y=0)
        image.save()
    except IntegrityError:
        # guess it wasn't unique... tell the caller
        return False

    # try and read the EXIF orientation from the image. some cameras produce a
    # sideways image, then set the tag to tell the viewer to rotate it
    # accordingly. since we throw away the EXIF data, such an image would end up
    # sideways unless we read the orientation and rotated it ourselves
    orientation = get_exif_orientation(orig_data)

    # now we run the image through jpegtran for all the security benefits
    # discussed earlier. jpegtran also losslessly applies the EXIF orientation.
    rebuilt_data = jpegtran(orig_data, orientation)

    # from that data, we can more safely use Pillow to create a thumbnail
    image_size, thumb_data, thumb_size = make_thumbnail(rebuilt_data)

    # calculate an appropriate filename. we take all the nice characters from
    # the original, but not so many that we don't have room for the rest of the
    # filename.
    if name.startswith("."): # stop any hidden filename funny business
        name = "_"+name
    name = re.sub(r'[^0-9a-zA-z_\-.]', '_', name)[:128]

    # add on the hash (extension is added as necessary)
    name = "{}_{}".format(name, image_hash.hex())
    # we are certain this filename won't collide with any other because it
    # includes the hash and we already made sure there are no other images with
    # the same hash

    # finally, we can save the file to disk and update the database record
    image_path = settings.L_IMAGE_PATH/(name+".jpg")
    thumb_path = settings.L_IMAGE_PATH/(name+"_thumb.jpg")
    succeeded = False
    try:
        with transaction.atomic():
            image.file_path = name # without extension
            image.deleted = False
            image.uploaded = True
            image.image_x = image_size[0]
            image.image_y = image_size[1]
            image.save()

            f = open(image_path, "wb")
            f.write(rebuilt_data)
            f.close()

            f = open(thumb_path, "wb")
            f.write(thumb_data)
            f.close()
        succeeded = True
    finally:
        if not succeeded:
            # try to not leave useless files lingering
            try:
                image_path.unlink()
            except:
                pass
            try:
                thumb_path.unlink()
            except:
                pass

    return True
