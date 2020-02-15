# serve the various static files that the LabelMe tool needs. according to
# everyone, this is the most horrendous and horrible approach in existence and
# my webserver should be doing it etc etc. but for now this works. we will want
# to change later so we can compress the js/css and ensure correct cache
# behavior and reduce server load.

from django.http import HttpResponse

import shutil
import pathlib
import mimetypes

lm_dir = pathlib.Path(__file__).parent.absolute()/"LabelMeAnnotationTool"

# return an HttpResponse of the given file relative to the label me stuff
def lm_serve(path):
    f = open(lm_dir/path, "rb")
    resp = HttpResponse(content_type=mimetypes.guess_type(path)[0])
    shutil.copyfileobj(f, resp)
    f.close()
    return resp

def tool(request):
    return lm_serve("tool.xhtml")

def lm_static(request, file, dir):
    return lm_serve(dir+"/"+file)

