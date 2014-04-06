#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import select
import re
import socket
import sys
import yaml
import os

# YAML config
if os.path.exists(os.path.dirname(__file__) + '/xpl2fibaro.yaml'):
    conf = file(os.path.dirname(__file__) + '/xpl2fibaro.yaml', 'r')
    conf = yaml.load(conf)
else:
    print 'Please add a xpl2fibaro.yaml !'
    sys.exit(1)

# API URLS
fibaro_ip = conf['fibaro']['ip']
url_devices = 'http://' + fibaro_ip + '/api/devices'
url_vdevices = 'http://' + fibaro_ip + '/api/virtualDevices'
url_variables = 'http://' + fibaro_ip + '/api/globalVariables'
# API log/pass
user = conf['fibaro']['user']
passwd = conf['fibaro']['passwd']

# XPL
buff = 1500
port = 3865

# Init local cache
local_cache = []

noop = False
debug = False
xpl = False


def checkIfDeviceNotExist(device):
    'Test if device exist in HomeCenter'

    if device in local_cache:
        return False

    resp = requests.get(url=url_vdevices, auth=(user, passwd))

    if resp.status_code == 200:
        data = json.loads(resp.content)
        for vdevice in data:
            idRfxDevice = re.search('-- idRfx (.*)\n',
                                    vdevice['properties']['mainLoop'])

            try:
                idRfxDevice.group(1)
            except:
                ""
            else:
                if device == idRfxDevice.group(1):
                    if device not in local_cache:
                        local_cache.append(device)
                        return False
                        break

        return True

    else:
        return 'Error with Fibaro API on check device - HTTP CODE : ' + resp.status_code

# Params
if '--noop' in sys.argv:
    noop = True
    print '- noop mode -'

if '--debug' in sys.argv:
    debug = True
    print '- debug mode -'

if '--xpl' in sys.argv:
    xpl = True
    print '- xpl mode -'

# Initialise the socket
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
addr = ('0.0.0.0', port)

# Bind
try:
    UDPSock.bind(addr)
except:
    print 'Port ' + str(port) + ' already used !'
    sys.exit(1)

print 'xPL Monitor for Python, bound to port ' + str(port)

while 1 == 1:
    readable, writeable, errored = select.select([UDPSock], [], [], 60)

    if len(readable) == 1:
        data, addr = UDPSock.recvfrom(buff)
        sensor = re.search('sensor.basic(.*)', data)

        try:
            sensor.group(1)
        except:
            print 'Not sensor line...'
        else:
            if xpl:
                print data

            device = re.search('device=(\S+)[0-9] (\S+)', data)
            idRfx = device.group(2)

            if device.group(1) == 'th' or device.group(1) == 'temp' or device.group(1) == 'rain' or device.group(1) == 'elec':
                if debug:
                    print 'Devices in cache : ' + str(local_cache)
                dtype = re.search('type=(\w+)', data)
                value = re.search('current=(.*)', data)

                print idRfx + ' - ' + dtype.group(1) + ' - ' + value.group(1)

                if checkIfDeviceNotExist(idRfx) and not noop:
                    try:
                        conf['devices'][idRfx]
                    except:
                        print 'Please configure a device with ' + idRfx + ' id...'
                    else:
                        # device idRfx doest not exist
                        payload = {'name': 'ToSet'}

                        newdevice = requests.post(url=url_vdevices,
                                                  auth=(user, passwd),
                                                  data=payload)

                        newdevice = json.loads(newdevice.content)
                        newdevice_id = str(newdevice['id'])
                        if debug:
                            print 'New device created : ' + newdevice_id
                        newDeviceData = {
                            "id": int(newdevice_id),
                            "name": conf['devices'][idRfx]['name'],
                            "properties":
                            {
                                "deviceIcon": conf['devices'][idRfx]['icon'],
                            }
                        }

                        rows = []
                        i = 0

                        mainLoop_head = "-- idRfx " + idRfx + "\nlocal selfId = fibaro:getSelfId()"

                        mainLoop_battery = """
                        local battery = fibaro:getGlobal('battery_%(idRfx)s')
                        """ % {'idRfx': idRfx}

                        mainLoop_foot = """
                        fibaro:log("Battery : " .. battery .. "%")
                        fibaro:debug('Sleep 60 sec, then restart')
                        fibaro:sleep(60*1000)
                        """

                        mainLoop_devices = []


                        for n in conf['devices'][idRfx]['rows']:
                            name = conf['devices'][idRfx]['rows'][i]['name']
                            main = conf['devices'][idRfx]['rows'][i].get('main', False)
                            caption = conf['devices'][idRfx]['rows'][i]['caption']
                            unit = conf['devices'][idRfx]['rows'][i]['unit']

                            tmp_row = {
                                "type": "label",
                                "elements": [
                                    {
                                        "id": i,
                                        "caption": caption,
                                        "name": name,
                                        "main": main
                                    }
                                ]
                            }

                            mainLoop_temp = """
                            local %(name)s = fibaro:getGlobal('%(name)s_%(idRfx)s')
                            fibaro:call(selfId, "setProperty", "ui.%(name)s.value", %(name)s .. "%(unit)s")
                            """ % {'name': name, 'idRfx': idRfx, 'unit': unit}

                            i += 1
                            rows.append(tmp_row)
                            mainLoop_devices.append(mainLoop_temp)


                        newDeviceData['properties']['rows'] = rows
                        mainLoop = mainLoop_head + mainLoop_battery + ('\n').join(mainLoop_devices) + mainLoop_foot
                        newDeviceData['properties']['mainLoop'] = re.sub('^\s+', '', mainLoop, flags=re.MULTILINE)

                        if debug:
                            print 'json : ' + json.dumps(newDeviceData)

                        newdevice = requests.put(url=url_vdevices,
                                                 auth=(user, passwd),
                                                 data=json.dumps(newDeviceData))

                        if newdevice.status_code == 200:
                            local_cache.append(idRfx)
                        else:
                            print 'Problem with fibaro API - HTTP CODE : ' + newdevice.status_code

                else:
                    if xpl:
                        print data

                payload = { 'name': dtype.group(1) + '_' + idRfx, 'value': value.group(1) }
                variables = requests.post(url=url_variables, auth=(user, passwd), data=payload)
                if variables.status_code == 409:
                    variables = requests.put(url=url_variables, auth=(user, passwd), data=json.dumps(payload))
