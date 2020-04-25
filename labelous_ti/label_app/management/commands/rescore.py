# go through all the annotations in the database and recompute their scores

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

from datetime import datetime, timezone

from browser.models import User
from label_app.models import Annotation, Polygon
from label_app.views import load_object_scores

class Command(BaseCommand):
    help = "Recompute scores for all annotations in the database."

    def add_arguments(self, parser):
        parser.add_argument("--save", action="store_true",
            help="Save recomputed scores to the database.")

    def handle(self, *args, **options):
        do_save = options["save"]

        object_scores = load_object_scores()

        for anno in Annotation.objects.filter(deleted=False).only("pk"):
            with transaction.atomic():
                # reselect the annotation for update so nobody else can touch it
                # until we are done with it (and vice versa)
                anno = Annotation.objects.select_for_update().get(pk=anno.pk)

                # get all the labels for this annotation
                polys = anno.polygons.filter(deleted=False).only("label_as_str")
                # then tally up the score
                score = sum(object_scores.get(p.label_as_str, 0) for p in polys)

                if anno.finished:
                    state = "finished"
                elif anno.locked:
                    state = "awaiting review"
                else:
                    state = "in progress"

                if anno.score != score:
                    print("by:", anno.annotator.email, state,
                        anno.score, score)

                    # save the updated score back to the database. we don't
                    # change the edit key because a) we've calculated an
                    # accurate score since nobody else is touching this
                    # annotation right now and b) edits will recalculate the
                    # score anyway.
                    if do_save:
                        anno.last_edit_time = datetime.now(timezone.utc)
                        anno.score = score
                        anno.save()
