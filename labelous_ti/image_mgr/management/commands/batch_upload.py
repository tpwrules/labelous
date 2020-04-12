# upload a pile of images from the given list. the given list has one path per
# line, where each path points to a specific image to upload. it outputs the
# uploaded image info into a comma separated list, where each line is
# image_pk,status,path. 

from django.db import transaction
from django.core.management.base import BaseCommand, CommandError

import pathlib

from browser.models import User
from image_mgr.models import Image
from image_mgr.process_image import (process_image, MAX_IMAGE_SIZE,
    ProcessingFailure, UnacceptableImage)

class Command(BaseCommand):
    help = "Regenerate thumbnails for all images in the database."

    def add_arguments(self, parser):
        parser.add_argument("file_list", type=str)
        parser.add_argument("output_list", type=str)

    def handle(self, *args, **options):
        file_list = pathlib.Path(options["file_list"]).resolve(strict=True)
        output_list = pathlib.Path(options["output_list"])
        if output_list.exists():
            raise Exception("output list already exists")

        file_list = open(file_list, "r")
        output_list = open(output_list, "w")

        # figure out who to upload as. we use the superuser with the lowest ID
        # because they're like the ultra-super user.
        uploader = User.objects.filter(
            is_superuser=True).order_by('pk')[:1].get()
        print("Uploading as '{}'".format(uploader))

        for file_name in file_list:
            try:
                file_name = pathlib.Path(file_name.replace("\n", ""))
                image_file = open(file_name, "rb")
                image_data = image_file.read(MAX_IMAGE_SIZE+1)
                image_file.close()
            except Exception as e:
                msg = ",read_error:{},{}\n".format(
                    str(e).replace(","," "), file_name)
                print(msg, end="")
                output_list.write(msg)
                continue

            if len(image_data) > MAX_IMAGE_SIZE:
                msg = ",too_big,{}\n".format(file_name)
                print(msg, end="")
                output_list.write(msg)
                continue

            try:
                new_image = process_image(uploader=uploader,
                    name=file_name.name, orig_data=image_data)
            except ProcessingFailure as e:
                msg = ",corrupt:{},{}\n".format(
                    str(e).replace(","," "), file_name)
                print(msg, end="")
                output_list.write(msg)
            except UnacceptableImage as e:
                msg = ",unacceptable:{},{}\n".format(
                    str(e).replace(","," "), file_name)
                print(msg, end="")
                output_list.write(msg)
            else:
                msg = "{},ok,{}\n".format(
                    new_image.pk, file_name)
                print(msg, end="")
                output_list.write(msg)

        file_list.close()
        output_list.close()
        print("Complete")
