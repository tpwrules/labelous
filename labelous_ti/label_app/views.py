from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import SuspiciousOperation
from django.db import transaction

from xml.sax.saxutils import escape as xml_escape
import defusedxml.ElementTree
import types
from datetime import datetime, timezone

from . import models
import image_mgr.models

def get_annotation_xml(request, image_id):
    # regex only allows numbers through
    image_id = int(image_id)

    try:
        image = image_mgr.models.Image.objects.get(pk=image_id)
        exists = True
    except image_mgr.models.Image.DoesNotExist:
        exists = False
        # we don't check for if multiple exist, because if that happens,
        # something has gone horrifically wrong in the database.

    if image.visible is False:
        exists = False
    else:
        try:
            annotation = models.Annotation.objects.get(
                annotator=request.user, image=image, deleted=False)
        except models.Annotation.DoesNotExist:
            exists = False
            # if multiple un-deleted annotations exist, something has gone
            # terribly wrong.

    if not exists:
        raise Http404("Annotation does not exist.")

    # load all the visible polygons attached to this annotation
    polygons = annotation.polygons.filter(deleted=False)

    # because XML is hard and bad, we build the result with string operations.
    xml = ["<annotation>"]
    # the annotation tool doesn't rebuild the document, it only modifies it.
    # this means we can attach arbitrary tags (which we prefix with c_) and they
    # will be returned untouched. it also means that most of the formatting we
    # apply will be preserved. formatting is wasted bytes, so we don't put it
    # in.

    # write which annotation ID this represents. we don't get anything other
    # than the xml when this document is returned, so we need it to look back up
    # where it came from.
    xml.append("<c_anno_id>{}</c_anno_id>".format(annotation.pk))
    # specify which image file to show for this annotation. since we look up
    # images by their ID, the folder doesn't matter as long as it's constant.
    xml.append("<filename>img{}.jpg</filename><folder>f</folder>".format(
        image_id))
    for polygon in polygons:
        xml.append("<object>")
        # we need to know the polygon ID so we can update the record if the user
        # changed the points
        xml.append("<c_poly_id>{}</c_poly_id>".format(polygon.pk))
        # the polygon's label as text
        xml.append("<name>{}</name>".format(xml_escape(polygon.label_as_str)))
        # if deleted is 1, the polygon won't show up. we avoid sending deleted
        # polygons, so there's no case it would be set to 1.
        # if verified is 1, the polygon will show an error if the user tries to
        # edit it. we map this to the polygon's locked status.
        xml.append("<deleted>0</deleted><verified>{}</verified>".format(
            1 if polygon.locked or annotation.locked else 0))
        # whether the user considers the polygon to be occluded. same as
        # database flag.
        xml.append("<occluded>{}</occluded>".format(
            "yes" if polygon.occluded else "no"))
        # any additional notes the user wants to put.
        xml.append("<attributes>{}</attributes>".format(
            xml_escape(polygon.notes)))
        # now the actual polygon points. we need to specify the user that
        # created the polygon. so the tool is happy, we claim this is always the
        # logged in user (or for now, a constant user.)
        xml.append("<polygon><username>hi</username>")
        points = polygon.points
        # points are stored as a flat array: even indices are x and odd are y
        for pi in range(0, len(points), 2):
            # the tool can send non-integer coordinates even if they are a
            # little silly. we specify a limit of 2 decimal places to get good
            # accuracy and make sure the numbers are reasonable length.
            # (i.e. not 3.5000000000000000069 or w/e)
            xml.append("<pt><x>{:.2f}</x><y>{:.2f}</y></pt>".format(
                points[pi], points[pi+1]))
        xml.append("</polygon></object>")
    xml.append("</annotation>")

    # django will automatically concatenate our xml strings
    return HttpResponse(xml, content_type="text/xml")


# handle a returned annotation XML document. note that we get no additional
# information, just what's inside the xml. also note that we have to be
# intensely suspicious of its contents, because the labeling tool performs no
# validation of any kind at all whatsoever (and any whacko could POST whatever
# XML they wanted to anyway). if anything is weird, we throw a
# SuspiciousOperation exception, which causes the tool to reload and get the
# correct annotations back from the database.

# handle understanding the document and updating the database. if this raises
# any kind of exception, the database transaction is rolled back.
def process_annotation_xml(request, root):
    if root.tag != "annotation":
        raise SuspiciousOperation("not an annotation")

    # look up the image we are allegedly annotating
    try:
        filename = root.find("filename").text
        if not filename.startswith("img") or not filename.endswith(".jpg"):
            raise Exception("invalid filename {}".format(filename))
        image_id = int(filename[3:-4])
        image = image_mgr.models.Image.objects.get(pk=image_id)
        if not image.visible:
            raise Exception("invisible image")
    except Exception as e:
        raise SuspiciousOperation("invalid image") from e

    # look up the annotation this document is allegedly for
    try:
        anno_id = int(root.find("c_anno_id").text)
        annotation = models.Annotation.objects.get(
            annotator=request.user, image=image, locked=False, deleted=False)
        if annotation.deleted:
            raise Exception("deleted annotation")
    except Exception as e:
        raise SuspiciousOperation("invalid anno id") from e

    # pull out all the polygons defined in this document. once that is done, we
    # will apply them to the database.
    anno_polygons = []
    anno_poly_ids = set()
    for obj_tag in root.findall("object"):
        anno_polygon = types.SimpleNamespace()
        try:
            # newly-created polygons won't have IDs
            if obj_tag.find("c_poly_id") is None:
                anno_polygon.id = None
            else:
                # it has an ID and it must be correct
                anno_polygon.id = int(obj_tag.find("c_poly_id").text)
                if anno_polygon.id in anno_poly_ids:
                    raise Exception("duplicate id")
                anno_poly_ids.add(anno_polygon.id)

            anno_polygon.name = obj_tag.find("name").text
            if anno_polygon.name == "":
                raise Exception("empty name")

            deleted = int(obj_tag.find("deleted").text)
            if deleted not in (0, 1):
                raise Exception("bad deleted")
            anno_polygon.deleted = False if deleted == 0 else True

            occluded = obj_tag.find("occluded").text
            if occluded not in ("no", "yes"):
                raise Exception("bad occluded")
            anno_polygon.occluded = False if occluded == "no" else True

            try:
                attributes = obj_tag.find("attributes").text
            except:
                attributes = None
            anno_polygon.attributes = "" if attributes == None else attributes

            anno_polygon.points = []
            try:
                for point_tag in obj_tag.find("polygon").findall("pt"):
                    # this double-conversion makes sure the numbers are received
                    # with the same precision we send them, and thus avoids
                    # problems where the number didn't change but isn't quite
                    # equal to what the database has.
                    x = float("{:.2f}".format(float(point_tag.find("x").text)))
                    y = float("{:.2f}".format(float(point_tag.find("y").text)))
                    anno_polygon.points.extend((x, y))
            except:
                raise Exception("bad points")

            anno_polygons.append(anno_polygon)
        except Exception as e:
            raise SuspiciousOperation("invalid polygon") from e

    # get the polygons attached to this annotation that can be shown
    polygons = annotation.polygons.filter(deleted=False)
    # and map them by their ID
    polygons = {p.pk: p for p in polygons}
    with transaction.atomic():
        # mesaure if anything changed in the annotation so we can update its
        # last edited time.
        annotation_changed = False
        for anno_poly in anno_polygons:
            # mesaure if anything changed in the polygon so we can update its
            # last edited time.
            polygon_changed = False
            poly = polygons[anno_poly.id]

            if poly.deleted and not anno_poly.deleted:
                raise SuspiciousOperation("undeleting is verboten")

            if poly.label_as_str != anno_poly.name: polygon_changed = True
            if poly.notes != anno_poly.attributes: polygon_changed = True
            if poly.occluded != anno_poly.occluded: polygon_changed = True
            if poly.points != anno_poly.points: polygon_changed = True
            if poly.deleted != anno_poly.deleted: polygon_changed = True
            if polygon_changed: print("poly changed!!")

            if polygon_changed:
                poly.label_as_str = anno_poly.name
                poly.notes = anno_poly.attributes
                poly.occluded = anno_poly.occluded
                poly.points = anno_poly.points
                poly.deleted = anno_poly.deleted
                poly.last_edit_time = datetime.now(timezone.utc)
                poly.save()
                annotation_changed = True

        if annotation_changed:
            annotation.last_edit_time = datetime.now(timezone.utc)
            annotation.save(update_fields=('last_edit_time',))


# parse the XML data. the request can't be, by default, bigger than 2.5MiB, so
# it shouldn't consume too much memory. the options given to parse prevent
# expansion attacks and external sourcing garbage.
def parse_annotation_xml(request):
    try:
        # empirically, the request seems to be utf8
        xml = defusedxml.ElementTree.fromstring(request.body.decode("utf8"),
            forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except Exception as e:
        raise SuspiciousOperation("xml parse failed") from e

    try:
        process_annotation_xml(request, xml)
    except SuspiciousOperation:
        raise
    except Exception as e:
        raise SuspiciousOperation("xml process failed") from e

# DANGER!!!! CSRF should be used to prevent forged annotations from being
# uploaded. but that would require hacking labelme to properly transmit the
# token. apparently django stores it in a cookie so this could be done later.
@csrf_exempt
def post_annotation_xml(request):
    try:
        parse_annotation_xml(request)
    except Exception:
        import traceback
        traceback.print_exc()
        raise

    # since the data was posted by XHR, we are expected to reply with SOME kind
    # of XML. what that is doesn't matter.
    return HttpResponse("<nop/>", content_type="text/xml")
