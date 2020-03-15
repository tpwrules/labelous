# regenerate thumbnails for all the images.
# useful if the settings changed.

from django.core.management.base import BaseCommand, CommandError

from image_mgr.models import Image
from image_mgr.process_image import make_thumbnail

class Command(BaseCommand):
    help = "Regenerate thumbnails for all images in the database."

    def add_arguments(self, parser):
        pass # no arguments

    def handle(self, *args, **options):
        for image in Image.objects.filter(uploaded=True, deleted=False).all():
            self.stdout.write(image.file_path+"... ", ending="")
            try:
                f = open(image.image_path, "rb")
                image_data = f.read()
                f.close()

                _, thumb_data, _ = make_thumbnail(image_data)

                f = open(image.thumb_path, "wb")
                f.write(thumb_data)
                f.close()
            except Exception as e:
                self.stdout.write(str(e))
            else:
                self.stdout.write("OK!")
