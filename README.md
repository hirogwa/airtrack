# airtrack
airport time sheet utility

### prerequisite
* Python 3.5

### install
```
$ pip install .
```

### run
Modify settings.py as necessary.
```
$ # initialize (first time only)
$ airtrack init_db
$
$ # register the data point
$ airtrack register
```

### run as daemon
Modify the .plist file as necessary.
```
$ # register
$ ln -s /path/to/resources/airtrack.plist ~/Library/LaunchAgents/net.hirogwa.airtrack.plist
$
$ # load
$ launchctl load ~/Library/LaunchAgents/net.hirogwa.airtrack.plist
$
$ # unload
$ launchctl unload ~/Library/LaunchAgents/net.hirogwa.airtrack.plist
```

## license
Released under [MIT] (http://opensource.org/licenses/MIT)
