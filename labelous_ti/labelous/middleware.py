from django.utils import timezone

def WhenReceivedMiddleware(get_response):
    def middleware(request):
        # add when the request was received (and processed by this middleware)
        # so we have a fixed reference point for e.g. update times and contest
        # participation time validation
        request.when = timezone.now()

        # we don't need to do anything to the response
        return get_response(request)

    return middleware
