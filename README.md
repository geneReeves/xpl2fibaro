xpl2fibaro
==========

python script for create hc2 virtuals devices from rfxcom xPL datas.
Works with Oregon weather sensors, rain sensor PCR800, power sensor OWL CM160

# Requirements
- lockfile >= 0.9.1
- python-daemon >= 1.6
- requests

# Usage

- start : `python xpl2fibaro.py start`
- stop  : `python xpl2fibaro.py stop`

# Configuration
You need a config file *xpl2fibaro.yaml*

You can start with :
```
process:
  debug: False
  xpl: False
  noop: False
fibaro:
  ip: '192.168.1.160'
  user: 'admin'
  passwd: 'admin'
devices:
```

# Fist run
Start *xpl2fibaro.py* daemon then look the log file created in the same directory. Its looks like :
```
2014-04-07 23:44:28,837 - xpl2fibaro - INFO - 0x2202 - temp - 14.7
2014-04-07 23:44:28,883 - xpl2fibaro - INFO - 0x2202 - humidity - 26
2014-04-07 23:44:28,931 - xpl2fibaro - INFO - 0x2202 - battery - 100
```

And for each devices you want, add it in the config file. For example, to add this Oregon device *0x2202* :
```
devices:
  '0x2202':
    name: 'Température'
    icon: 1019
    rows:
      - name: 'temp'
        caption: 'T°'
        unit: '°C'
        main: true
      - name: 'humidity'
        caption: 'Humidité'
        unit: '%'
```
Look inside my *xpl2fibaro.yaml* for a full example. You need to restart the daemon to apply your changes.


# Result on HC2

![alt tag](https://raw.githubusercontent.com/eremid/xpl2fibaro/master/hc2_temp.png)

![alt tag](https://raw.githubusercontent.com/eremid/xpl2fibaro/master/hc2_temp2.png)

![alt tag](https://raw.githubusercontent.com/eremid/xpl2fibaro/master/rain_and_power.png)
