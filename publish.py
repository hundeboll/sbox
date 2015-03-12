#!/usr/bin/env python2

from threading import Thread as thread
from threading import Event as event
import pybonjour
import logging
import select
import sys

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class publish(object):
    def __init__(self, config):
        self.stopping = event()
        self.config = config
        self.zeroconf = None
        self.setup()

    def registered(self, zeroconf, flags, errorCode, name, regtype, domain):
        if errorCode == pybonjour.kDNSServiceErr_NoError:
            log.debug("service registered")

    def setup(self):
        regtype = "_http._tcp."
        name = "sbox"
        port = self.config.http_port
        properties = {
                      "path": self.config.http_path,
                      "proto": self.config.http_proto,
                      "name": self.config.http_name,
                     }
        txt_record = pybonjour.TXTRecord(properties)

        self.zeroconf = pybonjour.DNSServiceRegister(name=name,
                                                     regtype=regtype,
                                                     port=port,
                                                     callBack=self.registered,
                                                     txtRecord=txt_record)

    def run(self):
        while not self.stopping.is_set():
            ready = select.select([self.zeroconf], [], [], .1)

            if self.stopping.is_set():
                break

            if self.zeroconf in ready[0]:
                pybonjour.DNSServiceProcessResult(self.zeroconf)

    def start(self):
        self.thread = thread(None, self.run, "publish")
        self.thread.start()
        log.debug("started")

    def stop(self):
        if not self.zeroconf:
            return

        self.stopping.set()
        self.zeroconf.close()
        self.zeroconf = None
        self.thread.join()
        log.debug("stopped")
