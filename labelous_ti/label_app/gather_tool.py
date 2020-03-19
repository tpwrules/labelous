# this script gathers all the files needed by the tool and installs them into
# the static files dir

import pathlib
import re

# get the input and output directoriess
script_dir = pathlib.Path(__file__).resolve(strict=True).parent
tool_dir = (script_dir/"LabelMeAnnotationTool").resolve(strict=True)

# the first thing we have to do is put the django template stuff into the
# tool.xhtml. the stuff compresses the CSS and JS so the user doesn't have to
# download 37 files. it also deals with cache-busting for us so the stuff can be
# cached.
tool = open(tool_dir/"tool.xhtml", "r").read()
tool = tool.replace("<!--LOAD_COMPRESS-->", "{% load compress %}")
tool = tool.replace("<!--COMPRESS_JS-->", "{% compress js %}")
tool = tool.replace("<!--COMPRESS_CSS-->", "{% compress css %}")
tool = tool.replace("<!--ENDCOMPRESS-->", "{% endcompress %}")

# then we need to figure out what files the tool depends on
resources = set()
script_pattern = re.compile(
    r'<script type="text/javascript" src="(.*?)"></script>')
css_pattern = re.compile(
    r'<link rel="stylesheet" href="(.*?)" type="text/css" />')
src_pattern = re.compile(r'src="(.*?)"')
for script in script_pattern.findall(tool):
    resources.add(script)
for stylesheet in css_pattern.findall(tool):
    resources.add(stylesheet)
resources.update([
    # the favicon isn't matched by any of those patterns or the src we do below
    "Icons/favicon16.ico",
    # and we need the on-brand CSS for the browser component
    "browserTools/css/accordion.css",
    "browserTools/css/gallery4.css",
    "browserTools/css/main4.css",
])

# one file the tool depends on is the names of all the priority objects. we have
# to make that file especially for it.
objects = []
with open(script_dir/"label_priorities.txt", "r") as priorities:
    for obj in priorities.readlines():
        objects.append(obj.split(",", 1)[1][:-1])
objects.sort()
obj_script = ['<script type="text/javascript">']
obj_script.append("var object_choices = [")
for obj in objects:
    obj_script.append('"{}",'.format(obj))
obj_script.append("]")
obj_script.append("</script>")
tool = tool.replace("<!--OBJECT_LIST-->", "\n".join(obj_script))

# now we need to update the tool page with the new static links we're gonna make
def to_static(path):
    return "/static/label_app/"+path.split("/")[-1]
for resource in resources:
    tool = tool.replace(resource, to_static(resource))

# there are other resources that need to be updated in the page, like images.
# since image links are also in the resources (js html snippets) we make this
# a function.
def update_resources(page):
    for link in src_pattern.findall(page):
        if not link.startswith("/static"): # not yet converted by something else
            page = page.replace(link, to_static(link))
            resources.add(link)
    return page
tool = update_resources(tool)
# we've made it a django template, so it has to go in the appropriate place
f = open(script_dir/"templates"/"label_app"/"tool.html", "w")
f.write(tool)
f.close()

# search in the js files for stuff and write them out
js_resources = set(rsrc for rsrc in resources if rsrc.endswith(".js"))
resources -= js_resources
for resource in js_resources:
    fin = open(tool_dir/resource, "r")
    page = fin.read()
    fin.close()
    page = update_resources(page)
    fout = open(script_dir/to_static(resource)[1:], "w")
    fout.write(page)
    fout.close()

# then finally, copy over the rest of the resources
for resource in resources:
    fin = open(tool_dir/resource, "rb")
    page = fin.read()
    fin.close()
    fout = open(script_dir/to_static(resource)[1:], "wb")
    fout.write(page)
    fout.close()
