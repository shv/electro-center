from django.http import HttpResponse
from jsonview.decorators import json_view #https://pypi.python.org/pypi/django-jsonview
from .models import Pin
import logging
import os
import random

logger = logging.getLogger(__name__)


node_id = os.environ.get('IHOME_ARDUINO_ID', 1)

# Emulation of node
@json_view
def status(request):
    logger.debug("Node = %s" % node_id)
    result = []
    for pin in  Pin.objects.filter(node=node_id).all():
        item = { "pin": pin.pin, "on": pin.on }
        if pin.dimmable:
            item['level'] = pin.level
        result.append(item)

    rand = round(random.random() * (800-300) + 300, 1)
    result.append({"value": rand, "pin": 16})
    rand = round(random.random() * (32-7) + 7, 1)
    result.append({"value": rand, "pin": 10, "sid": "28749423h4ih"})
    rand = round(random.random() * (32-7) + 7, 1)
    result.append({"value": rand, "pin": 10, "sid": "28749423h4i2"})
    return result


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

    result = []
    for pin in  Pin.objects.filter(node=node_id).all():
        item = { "pin": pin.pin, "on": pin.on }
        if pin.dimmable:
            item['level'] = pin.level
        result.append(item)

    rand = round(random.random() * (800-300) + 300, 1)
    result.append({"value": rand, "pin": 16})
    
    return result


@json_view
def dim(request):
    """Simple dim. For one pin only
    """
    req = request.GET.lists()
    logger.debug("Node = %s, req: %s" % (node_id, req))
    if len(req) == 1:
        logger.debug("Request: %s" % req[0][1][0])
        pin_id = req[0][0]
        logger.debug("Pin id: %s" % req[0][0])
        pin = Pin.objects.get(pin=pin_id, node=node_id)
        if int(req[0][1][0]) >=0 and int(req[0][1][0]) <= 100:
            logger.debug("Set new level %s" % req[0][1][0])
            pin.level = req[0][1][0]
        pin.save()

    result = []
    for pin in  Pin.objects.filter(node=node_id).all():
        item = { "pin": pin.pin, "on": pin.on }
        if pin.dimmable:
            item['level'] = pin.level
        result.append(item)

    rand = round(random.random() * (800-300) + 300, 1)
    result.append({"value": rand, "pin": 16})
    
    return result
