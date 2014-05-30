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
from daemon import runner
import logging
from logging.handlers import RotatingFileHandler

class App():
    def __init__(self):
        self.stdin_path = '/dev/null'
        self.stdout_path = '/dev/tty'
        self.stderr_path = '/dev/tty'
        self.pidfile_path = '/tmp/xpl2fibaro.pid'
        self.pidfile_timeout = 5


    def checkIfDeviceNotExist(self,device):
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

    def doSensor(self, device, idRfx, data):
        if debug:
            logger.debug('Devices in cache : ' + str(local_cache))

        dtype = re.search('type=(\w+)', data)
        value = re.search('current=(.*)', data)

        logger.info(idRfx + ' - ' + dtype.group(1) + ' - ' + value.group(1))

        if app.checkIfDeviceNotExist(idRfx) and not noop:
            try:
                conf['devices'][idRfx]
            except:
                logger.info('Please configure a device with ' + idRfx + ' id.')
            else:
                # device idRfx doest not exist
                payload = {'name': 'ToSet'}

                newdevice = requests.post(url=url_vdevices,
                                          auth=(user, passwd),
                                          data=payload)

                newdevice = json.loads(newdevice.content)
                newdevice_id = str(newdevice['id'])
                if debug:
                    logger.debug('New device created : ' + newdevice_id)

                newDeviceData = {
                    'id': int(newdevice_id),
                    'name': conf['devices'][idRfx]['name'],
                    'properties':
                    {
                        'deviceIcon': conf['devices'][idRfx]['icon'],
                    }
                }

                rows = []
                i = 0
                mainLoop_head = '-- idRfx ' + idRfx + '\nlocal selfId = fibaro:getSelfId()'

                mainLoop_battery = """
                local battery = fibaro:getGlobal('battery_%(idRfx)s')
                """ % {'idRfx': idRfx}

                mainLoop_foot = """
                fibaro:log('Battery : ' .. battery .. '%')
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
                        'type': 'label',
                        'elements': [
                            {
                                'id': i,
                                'caption': caption,
                                'name': name,
                                'main': main
                            }
                        ]
                    }

                    mainLoop_temp = """
                    local %(name)s = fibaro:getGlobal('%(name)s_%(idRfx)s')
                    fibaro:call(selfId, 'setProperty', 'ui.%(name)s.value', %(name)s .. '%(unit)s')
                    """ % {'name': name, 'idRfx': idRfx, 'unit': unit}

                    i += 1
                    rows.append(tmp_row)
                    mainLoop_devices.append(mainLoop_temp)

                    newDeviceData['properties']['rows'] = rows
                    mainLoop = mainLoop_head + mainLoop_battery + ('\n').join(mainLoop_devices) + mainLoop_foot
                    newDeviceData['properties']['mainLoop'] = re.sub('^\s+', '', mainLoop, flags=re.MULTILINE)

                    if debug:
                        logger.debug('json : ' + json.dumps(newDeviceData))

                    newdevice = requests.put(url=url_vdevices,
                                             auth=(user, passwd),
                                             data=json.dumps(newDeviceData))

                    if newdevice.status_code == 200:
                        local_cache.append(idRfx)
                    else:
                        logger.info('Problem with fibaro API - HTTP CODE : ' + newdevice.status_code)

        payload = {'name': dtype.group(1) + '_' + idRfx, 'value': value.group(1)}
        variables = requests.post(url=url_variables, auth=(user, passwd), data=payload)
        if variables.status_code == 409:
            variables = requests.put(url=url_variables, auth=(user, passwd), data=json.dumps(payload))

    def doAction(self, device, command):
        'Execute action on HC2'
        try:
            actions[device]
        except:
            logger.info('You need to add your device ' + device + ' in the conf.')
        else:
            try:
                actions[device]['modules']
            except:
                logger.info('No module in configuration file...')
            else:
                for m in actions[device]['modules']:
                    logger.info('%(command)s - module %(module)s' % {'command': command, 'module': m})
                    if command == 'on':
                        action = 'turnOn'
                    elif command == 'off':
                        action = 'turnOff'

                    payload = {'deviceID': m, 'name': action}
                    resp = requests.get(url=url_actions, auth=(user, passwd), params=payload)

                    if resp.status_code != 200 and resp.status_code != 202:
                        logger.info('Problem with API : %(status)s' % {'status': resp.status_code})

            if command == 'on':
                try:
                    actions[device]['scene_on']
                except:
                    logger.info('No scene in configuration file...')
                else:
                    for s_on in actions[device]['scene_on']:
                        logger.info('starting scene %(scene)s' % {'scene': s_on})
                        payload = {'id': s_on, 'action': 'start'}

                        resp = requests.get(url=url_scenes, auth=(user, passwd), params=payload)

                        if resp.status_code != 200 and resp.status_code != 202:
                            logger.info('Problem with API : %(status)s' % {'status': resp.status_code})

            if command == 'off':
                try:
                    actions[device]['scene_off']
                except:
                    logger.info('No scene in configuration file...')
                else:
                    for s_off in actions[device]['scene_off']:
                        logger.info('starting scene %(scene)s' % {'scene': s_off})
                        payload = {'id': s_off, 'action': 'start'}

                        resp = requests.get(url=url_scenes, auth=(user, passwd), params=payload)

                        if resp.status_code != 200 and resp.status_code != 202:
                            logger.info('Problem with API : %(status)s' % {'status': resp.status_code})


    def run(self):
        # Initialise the socket
        UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        addr = ('0.0.0.0', port)

        # Bind
        try:
            UDPSock.bind(addr)
        except:
            msg = 'Port ' + str(port) + ' already used !'
            logger.info(msg)
            print msg
            sys.exit(1)

        msg = 'xPL Monitor for Python, bound to port ' + str(port)
        logger.info(msg)

        while True:
            readable, writeable, errored = select.select([UDPSock], [], [], 60)

            if len(readable) == 1:
                data, addr = UDPSock.recvfrom(buff)

                if xpl:
                    logger.debug(data)

                sensor = re.search('xpl-trig(.*)', data)

                try:
                    sensor.group(1)
                except:
                    logger.info('Not a xpl-trig line...')
                    pass
                else:
                    device = re.search('(sensor|x10).basic(.*)', data)
                    try:
                        device.group(2)
                    except:
                        logger.info('Problem with device\n' + data)
                        pass
                    else:
                        type = device.group(1)
                        if type == 'sensor':
                            device = re.search('device=(\S+)[0-9] (\S+)', data)
                        elif type == 'x10':
                            device = re.search('device=(.*)', data)
                            command = re.search('command=(.*)', data)
                        try:
                            device.group(1)
                        except:
                            logger.info('I look for a device like device1 0x000 or (.*) for x10.sensor... not found here !')
                        else:
                            if type == 'x10':
                                app.doAction(device.group(1), command.group(1))
                            elif type == 'sensor':
                                app.doSensor(device.group(1), device.group(2), data)

app = App()

logger = logging.getLogger("xpl2fibaro")
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.FileHandler(os.path.dirname(__file__) + '/xpl2fibaro.log')
handler.setFormatter(formatter)
logger.addHandler(handler)


# YAML config
if os.path.exists(os.path.dirname(__file__) + '/xpl2fibaro.yaml'):
    conf = file(os.path.dirname(__file__) + '/xpl2fibaro.yaml', 'r')
    conf = yaml.load(conf)
else:
    msg = 'Please add a xpl2fibaro.yaml !'
    logger.info(msg)
    print msg
    sys.exit(1)

# API URLS
fibaro_ip = conf['fibaro']['ip']
actions = conf['actions']
url_devices = 'http://' + fibaro_ip + '/api/devices'
url_actions = 'http://' + fibaro_ip + '/api/callAction'
url_scenes = 'http://' + fibaro_ip + '/api/sceneControl'
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

# Params
if conf['process']['noop']:
    noop = True
    logger.info('- noop mode -')

if conf['process']['debug']:
    debug = True
    logger.info('- debug mode -')

if conf['process']['xpl']:
    xpl = True
    logger.info('- xpl mode -')

daemon_runner = runner.DaemonRunner(app)
daemon_runner.daemon_context.files_preserve = [handler.stream]
daemon_runner.do_action()
