from django.shortcuts import render
from django.http import HttpResponse, Http404
from django.conf import settings

from xml.sax.saxutils import escape as xml_escape

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
