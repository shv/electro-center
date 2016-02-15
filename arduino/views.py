from django.http import HttpResponse
from jsonview.decorators import json_view #https://pypi.python.org/pypi/django-jsonview
from .models import Pin
import logging
import os

logger = logging.getLogger(__name__)


node_id = os.environ.get('IHOME_ARDUINO_ID', 1)

# Emulation of node
@json_view
def status(request):
    logger.debug("Node = %s" % node_id)
    return [ { "pin": pin.pin, "on": pin.on } for pin in  Pin.objects.filter(node=node_id).all() ]


@json_view
def switch(request):
    """Simple switch. For one pin only
    """
    req = request.GET.lists()
    logger.debug("Node = %s, req: %s" % (node_id, req))
    if len(req) == 1 and req[0][1][0] in ['true', 'false']:
        logger.debug("Request: %s" % req[0][1][0])
        pin_id = req[0][0]
        logger.debug("Pin id: %s" % req[0][0])
        pin = Pin.objects.get(pin=pin_id, node=node_id)
        pin.on = True if req[0][1][0] == 'true' else False
        pin.save()


    return [ { "pin": pin.pin, "on": pin.on } for pin in  Pin.objects.filter(node=node_id).all() ]
