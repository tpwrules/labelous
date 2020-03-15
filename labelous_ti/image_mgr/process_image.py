# this file handles the whole image processing deal, from image data to disk
# storage, thumbnail generation, and database update.

from .models import Image

import PIL
import piexif

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

# The web allows the extra special category of polyglot-related skullduggery. 
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
# a completely new file. Theoretically, polyglots won't survive the process.
# However, an attacker could model jpegtran's actions and design a polyglot that
# could sneak through, but I'm not sure it's possible. Rosetta Flash-style
# attacks are stopped because the Huffman tables get rebuilt. All the comments
# and EXIF data are deleted (which also helps preserve the uploader's privacy),
# so nothing can hide there. The only remaining option is to generate an image
# whose encoded data looks like another file. But would it look like anything
# when decoded? The administrator might see an image that looks like garbage and
# discard it before it has a chance to do any damage.

# All that said, I'd like to see a try!

