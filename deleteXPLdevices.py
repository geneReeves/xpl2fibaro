#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import re
import sys

fibaro_ip = '192.168.1.160'
url_vdevices = 'http://' + fibaro_ip + '/api/virtualDevices'
url_variables = 'http://' + fibaro_ip + '/api/globalVariables'
user = 'admin'
passwd = 'admin'

noop = False

if '--noop' in sys.argv:
    noop = True
    print '- noop mode -'


def deleteDevice(id):
    "Delete a virtual device"
    if not noop:
        resp = requests.delete(url=url_vdevices + "?id=" + str(id), auth=(user, passwd))
        print "delete device " + str(id)

        if resp.status_code == 200:
            return 'deleted ...'
        else:
            return 'problem with delete'


def deleteGlobalVariable(id):
    "Delete a global variable"
    if not noop:
        resp = requests.delete(url=url_variables + "?name=" + id, auth=(user, passwd))
        print "delete variable " + id

        if resp.status_code == 200:
            return 'deleted ...'
        else:
            return 'problem with delete'


resp = requests.get(url=url_vdevices, auth=(user, passwd))
data = json.loads(resp.content)

for device in data:
    idRfxDevice = re.search('-- idRfx (.*)\n', device['properties']['mainLoop'])

    try:
        idRfx = idRfxDevice.group(1)
    except:
        ""
    else:
        print 'delete device ' + str(device['id'])
        deleteDevice(device['id'])
        print 'delete global variable'
        deleteGlobalVariable('temp_' + idRfx)
        deleteGlobalVariable('humidity_' + idRfx)
        deleteGlobalVariable('battery_' + idRfx)
        deleteGlobalVariable('rainrate_' + idRfx)
        deleteGlobalVariable('raintotal_' + idRfx)
        deleteGlobalVariable('energy_' + idRfx)
        deleteGlobalVariable('power_' + idRfx)
