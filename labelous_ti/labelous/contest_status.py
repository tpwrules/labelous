import datetime

# close 30 minutes after we claimed to let users get their last edits in
_contest_close_date = datetime.datetime(2021, 5, 6, 0, 30, 00)

def is_contest_open():
    return (datetime.datetime.now() < _contest_close_date)
