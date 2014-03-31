#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import select
import re
import socket
import sys

# API URLS
fibaro_ip = '192.168.1.160'
url_devices = 'http://' + fibaro_ip + '/api/devices'
url_vdevices = 'http://' + fibaro_ip + '/api/virtualDevices'
url_variables = 'http://' + fibaro_ip + '/api/globalVariables'
# API log/pass
user = 'admin'
passwd = 'admin'

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
            idThDevice = re.search('-- idTh (.*)\n',
                                   vdevice['properties']['mainLoop'])

            try:
                idThDevice.group(1)
            except:
                ""
            else:
                if device == idThDevice.group(1):
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
            idTh = device.group(2)

            if device.group(1) == 'th' or device.group(1) == 'temp':
                if debug:
                    print 'Devices in cache : ' + str(local_cache)
                dtype = re.search('type=(\w+)', data)
                value = re.search('current=(.*)', data)

                print idTh + ' - ' + dtype.group(1) + ' - ' + value.group(1)

                if checkIfDeviceNotExist(idTh) and not noop:
                    # device idTh doest not exist
                    payload = {'name': 'Température'}

                    newdevice = requests.post(url=url_vdevices,
                                              auth=(user, passwd),
                                              data=payload)

                    newdevice = json.loads(newdevice.content)
                    newdevice_id = str(newdevice['id'])
                    if debug:
                        print 'New device created : ' + newdevice_id

                    newDeviceDataTh = {
                        "id": int(newdevice_id),
                        "name": "Température",
                        "properties":
                        {
                            "deviceIcon": 1019,
                            "currentIcon": "0",
                            "mainLoop": "-- idTh " + idTh + "\nlocal selfId = fibaro:getSelfId()\nlocal temp = fibaro:getGlobal(\"temp_" + idTh + "\")\nlocal humidity = fibaro:getGlobal(\"humidity_" + idTh + "\")\nlocal battery = fibaro:getGlobal(\"battery_" + idTh + "\")\nfibaro:call(selfId, \"setProperty\", \"ui.temp.value\", temp..\" °C\")\nfibaro:call(selfId, \"setProperty\", \"ui.humidity.value\", humidity..\" %\")\nfibaro:log(\"Battery : \" .. battery .. \"%\")\nfibaro:debug(\"Sleep 60 sec, then restart\")\nfibaro:sleep(60*1000)",
                            "saveLogs": "1",
                            "rows": [
                                {
                                    "type": "label",
                                    "elements": [
                                        {
                                            "id": 1,
                                            "caption": "T°",
                                            "name": "temp",
                                            "main": True
                                        }
                                    ]
                                },
                                {
                                    "type": "label",
                                    "elements": [
                                        {
                                            "id": 2,
                                            "caption": "Humidité",
                                            "name": "humidity",
                                        }
                                    ]
                                }
                            ]
                        }
                    }

                    newDeviceDataTemp = {
                        "id": int(newdevice_id),
                        "name": "Température",
                        "properties":
                        {
                            "deviceIcon": 1019,
                            "currentIcon": "0",
                            "mainLoop": "-- idTh " + idTh + "\nlocal selfId = fibaro:getSelfId()\nlocal temp = fibaro:getGlobal(\"temp_" + idTh + "\")\nlocal battery = fibaro:getGlobal(\"battery_" + idTh + "\")\nfibaro:call(selfId, \"setProperty\", \"ui.temp.value\", temp..\" °C\")\nfibaro:log(\"Battery : \" .. battery .. \"%\")\nfibaro:debug(\"Sleep 60 sec, then restart\")\nfibaro:sleep(60*1000)",
                            "saveLogs": "1",
                            "rows": [
                                {
                                    "type": "label",
                                    "elements": [
                                        {
                                            "id": 1,
                                            "caption": "T°",
                                            "name": "temp",
                                            "main": True
                                        }
                                    ]
                                }
                            ]
                        }
                    }

                    newDeviceData = newDeviceDataTh if device.group(1) == 'th' else newDeviceDataTemp

                    if debug:
                        print 'json : ' + json.dumps(newDeviceData)

                    newdevice = requests.put(url=url_vdevices,
                                             auth=(user, passwd),
                                             data=json.dumps(newDeviceData))

                    if newdevice.status_code == 200:
                        local_cache.append(idTh)
                    else:
                        print 'Problem with fibaro API - HTTP CODE : ' + newdevice.status_code

                else:
                    if xpl:
                        print data

                payload = {'name': dtype.group(1) + '_' + idTh, 'value': value.group(1)}
                post = requests.post(url=url_variables, auth=(user, passwd), data=payload)
