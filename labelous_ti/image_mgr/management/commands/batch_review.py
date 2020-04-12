# review a pile of images from the given list. the given list has one image ID
# per line, optionally followed by a comma and whatever else. if something isn't
# an int, it's just skipped.

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

import pathlib

from image_mgr.models import Image

class Command(BaseCommand):
    help = "Regenerate thumbnails for all images in the database."

    def add_arguments(self, parser):
        parser.add_argument("review_action", type=str,
            choices=["accept", "delete"])
        parser.add_argument("image_list", type=str)

    def handle(self, *args, **options):
        image_list = pathlib.Path(options["image_list"]).resolve(strict=True)
        image_list = open(image_list, "r")

        image_ids = []
        for image_entry in image_list:
            image_entry = image_entry.replace("\n", "")
            if "," in image_entry:
                image_entry = image_entry.split(",", 1)[0]
            image_entry = image_entry.strip()
            try:
                image_id = int(image_entry)
            except ValueError:
                continue
            image_ids.append(image_id)

        print("Got {} image IDs".format(len(image_ids)))

        # only get images that haven't been reviewed
        images = Image.objects.filter(
            uploaded=True, deleted=False, available=False)

        if options["review_action"] == "accept":
            num_accepted = images.update(available=True)
            print("Accepted {} images".format(num_accepted))
        elif options["review_action"] == "delete":
            num_deleted = images.update(deleted=True)
            print("Deleted {} images".format(num_deleted))

        print("Complete")
