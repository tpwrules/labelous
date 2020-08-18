from django.conf import settings
from django.utils import timezone

import datetime

# CONTEST START AND END INFO

# these dates are in the settings.TIME_ZONE timezone

open_date = datetime.datetime(2020, 9, 8, 0, 0, 0,
    tzinfo=timezone.get_default_timezone())

close_date = datetime.datetime(2020, 9, 22, 23, 59, 59,
    tzinfo=timezone.get_default_timezone())

# we give a 30 minute grace period from the stated close date for people to get
# their last bits of work in
_real_close_date = close_date + datetime.timedelta(minutes=30)

# we've opened if 'when' is after the open date. note that we have still opened
# even after the close date!
def has_opened(when):
    return (open_date <= when)

# we've closed if 'when' is after the closed date.
def has_closed(when):
    return (_real_close_date < when)

def is_open(when):
    return has_opened(when) and not has_closed(when)
