#!/usr/bin/env python
# Copyright: 2016, Wasylews
# Author: Wasylews
# License: MIT

"""hilink-tray - display signal level for HiLink modems in a tray

Usage:
    hilink-tray.py [--timeout=N] [--ip=IP]
    hilink-tray.py -h | --help
    hilink-tray.py -v | --version

Options:
    -t N --timeout=N  download icon each N seconds
                      [default: 5]
    --ip=IP           modem ip
                      [default: 192.168.8.1]
    -v --version      show version
    -h --help         show this message and exit
"""

from __future__ import print_function
import docopt
import sys
from PySide import QtGui, QtCore
from PySide.phonon import Phonon
from xml.etree import ElementTree
import socket
from collections import OrderedDict
import res_rc

try:
    from urllib2 import build_opener, URLError
    from urlparse import urljoin
except ImportError:  # >= 3.x
    from urllib.request import build_opener
    from urllib.error import URLError
    from urllib.parse import urljoin


class ModemSignalChecker(QtCore.QThread):
    """Class for monitoring some modem parameters and send to gui"""
    levelChanged = QtCore.Signal(int, dict)

    def __init__(self, ip, timeout):
        super(ModemSignalChecker, self).__init__()
        self._url = "http://{}".format(ip)
        self._timeout = timeout
        self._running = True

    def stop(self):
        self._running = False

    def _getXml(self, opener, section):
        response = opener.open(urljoin(self._url, section))
        return ElementTree.fromstring(response.read())

    def getCookie(self, opener):
        try:
            xml = self._getXml(opener, "/api/webserver/SesTokInfo")
        except URLError:
            return ""
        else:
            return xml.find("SesInfo").text

    def getSignalLevel(self, xml):
        return int(xml.find("SignalIcon").text)

    def getNetworkType(self, xml):
        types = {"0": "No Service", "1": "GSM", "2": "GPRS", "3": "EDGE",
                 "41": "WCDMA", "42": "HSDPA", "43": "HSUPA", "44": "HSPA",
                 "45": "HSPA+", "46": "DC-HSPA+", "101": "LTE"}

        return types[xml.find("CurrentNetworkTypeEx").text]

    def getStatus(self, xml):
        states = {"900": "Connecting", "901": "Connected",
                  "902": "Disconnected"}
        return states[xml.find("ConnectionStatus").text]

    def getOperator(self, xml):
        return xml.find("FullName").text

    def getSignalParams(self, xml):
        params = ["rssi", "rsrp", "rsrq", "rscp", "ecio", "sinr",
                  "cell_id", "pci"]
        values = OrderedDict()

        for key in params:
            values[key] = "{key}: {val}".format(key=key.upper(),
                                                val=xml.find(key).text)
        return values

    def checkNotify(self, xml):
        return int(xml.find("UnreadMessage").text) > 0

    def getModemParams(self, opener):
        statusXml = self._getXml(opener, "/api/monitoring/status")
        level = self.getSignalLevel(statusXml)
        params = OrderedDict()

        plmnXml = self._getXml(opener, "/api/net/current-plmn")
        params["operator"] = "{} {}".format(self.getOperator(plmnXml),
                                            self.getNetworkType(statusXml))

        params["status"] = self.getStatus(statusXml)

        notifyXml = self._getXml(opener, "/api/monitoring/check-notifications")
        params["need_notify"] = self.checkNotify(notifyXml)

        signalXml = self._getXml(opener, "/api/device/signal")
        params.update(self.getSignalParams(signalXml))
        return (level, params)

    def run(self):
        opener = build_opener()
        cookie = self.getCookie(opener)
        opener.addheaders.append(("Cookie", cookie))

        while self._running:
            try:
                (level, params) = self.getModemParams(opener)
            except (URLError, socket.timeout):
                self.levelChanged.emit(0, {"status": "Disconnected"})
            else:
                self.levelChanged.emit(level, params)
            self.sleep(self._timeout)


class ModemIndicator(QtGui.QSystemTrayIcon):
    """Simple tray indicator"""

    def __init__(self, checker):
        super(ModemIndicator, self).__init__()
        menu = self.createMenu()
        self.setContextMenu(menu)
        self._checker = checker

        self.player = Phonon.createPlayer(Phonon.MusicCategory)
        self.player.stateChanged.connect(self._playerLog)

        self.updateStatus(0, {"status": "Disconnected"})

    def createMenu(self):
        menu = QtGui.QMenu()
        quitAction = QtGui.QAction("Quit", menu)
        quitAction.triggered.connect(self.close)
        menu.addAction(quitAction)
        return menu

    def close(self):
        self.hide()
        self._checker.stop()
        if not self._checker.wait(5000):
            self._checker.terminate()
            self._checker.wait()
        QtGui.qApp.quit()

    def signalIcon(self, level):
        if level in range(1, 6):
            return "://images/icons/icon_signal_0{}.png".format(level)
        return "://images/icons/icon_signal_00.png"

    def statusStr(self, params):
        tip = []
        for (key, value) in params.items():
            if value:
                tip.append(value)
        return "\n".join(tip)

    def updateStatus(self, level, params):
        icon = self.signalIcon(level)

        if params.pop("need_notify", False):
            # play notification sound
            source = Phonon.MediaSource("://sounds/sounds/unread_message.wav")
            self.player.setCurrentSource(source)
            self.player.play()
            # and change tray icon
            icon = "://images/icons/unread_message.gif"

        self.setToolTip(self.statusStr(params))
        self.setIcon(QtGui.QIcon(icon))

    def _playerLog(self, newState, oldState):
        if newState == Phonon.ErrorState:
            print(self.player.errorString())


def main(ip, timeout):
    app = QtGui.QApplication(sys.argv)
    checker = ModemSignalChecker(ip, timeout)
    tray = ModemIndicator(checker)
    checker.levelChanged.connect(tray.updateStatus)
    checker.start()
    tray.show()

    return app.exec_()

if __name__ == '__main__':
    args = docopt.docopt(__doc__, version="v2.0")
    ip = args["--ip"]
    timeout = int(args["--timeout"])
    sys.exit(main(ip, timeout))
