from django.http import HttpResponse
from jsonview.decorators import json_view #https://pypi.python.org/pypi/django-jsonview
from .models import Pin
import logging
import os

logger = logging.getLogger(__name__)


# Emulation of node
@json_view
def switch(request):
    req = dict(request.GET.lists())
    logger.debug(req)
    node_id = os.environ.get('IHOME_ARDUINO_ID', 1)
    logger.debug(node_id)
    on = req.get("on")
    if on:
        for pin_id in on:
            pin = Pin.objects.get(pin=pin_id, node=node_id)
            pin.on = True
            pin.save()

    off = req.get('off')
    if off:
        for pin_id in off:
            pin = Pin.objects.get(pin=pin_id, node=node_id)
            pin.on = False
            pin.save()

    return [ { "pin": pin.pin, "on": pin.on } for pin in  Pin.objects.filter(node=node_id).all() ]
