#!/usr/bin/env python2

import os
import sys
import flask
import logging
from functools import wraps
from threading import Thread as thread
from flask.ext.restful import reqparse

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

def check_spotify(func):
    @wraps(func)
    def wrapper(**kwargs):
        if not __s.spotify:
            return "spotify not available",503

        if not __s.spotify.is_logged_in():
            return "spotify not logged in",503

        return func(**kwargs)

    return wrapper

class __service_class(object):
    def __init__(self):
        self.app = flask.Flask(__name__)

    def set_spotify(self, spotify):
        self.spotify = spotify

    def set_config(self, config):
        self.config = config

    def start(self):
        self.thread = thread(None, self.run, "service thread")
        self.thread.start()
        log.debug("started")

    def stop(self):
        self.thread._Thread__stop()
        log.debug("stopped")

    def run(self):
        host = self.config.http_host
        port = self.config.http_port

        self.app.run(host=host, port=port)
        log.debug("done")

    def get_user_admins(self):
        return self.config.user_admins

__s = __service_class()

def service(config, spotify):
    __s.set_config(config)
    __s.set_spotify(spotify)
    return __s

@__s.app.route("/")
@check_spotify
def index():
    routes = [rule.endpoint for rule in __s.app.url_map.iter_rules()]

    return flask.jsonify(routes=routes)

@__s.app.route("/search", methods=["POST", "GET"])
@check_spotify
def search():
    log.debug("search request: data '{}', values: {}".format(flask.request.data,
                                                             flask.request.values.to_dict()))
    args = flask.request.get_json()

    if not args:
        args = flask.request.values.to_dict()

    s = __s.spotify.search(args)

    return flask.jsonify(s)

@__s.app.route("/playlist/add", methods=["POST", "GET"])
@check_spotify
def add():
    log.debug("add request: data '{}', values: {}".format(flask.request.data,
                                                          flask.request.values.to_dict()))
    args = flask.request.get_json()

    if not args:
        args = flask.request.values.to_dict()

    a = __s.spotify.playlist_add(args)

    return flask.jsonify(a)

@__s.app.route("/playlist/remove", methods=["POST", "GET"])
@check_spotify
def remove():
    log.debug("remove request: data '{}', values: {}".format(flask.request.data,
                                                             flask.request.values.to_dict()))
    args = flask.request.get_json()

    if not args:
        args = flask.request.values.to_dict()

    a = __s.spotify.playlist_remove(args)

    return flask.jsonify(a)

@__s.app.route("/playlist", methods=["POST", "GET"])
@check_spotify
def playlist():
    log.debug("artist request: data '{}', values: {}".format(flask.request.data,
                                                             flask.request.values.to_dict()))
    args = flask.request.get_json()

    if not args:
        args = flask.request.values.to_dict()

    log.debug("playlist request")
    p = __s.spotify.playlist_get(args)

    return flask.jsonify(p)

@__s.app.route("/artist", methods=["POST", "GET"])
@check_spotify
def artist():
    log.debug("artist request: data '{}', values: {}".format(flask.request.data,
                                                             flask.request.values.to_dict()))
    args = flask.request.get_json()

    if not args:
        args = flask.request.values.to_dict()

    a = __s.spotify.artist_get(args)

    return flask.jsonify(a)

@__s.app.route("/album", methods=["POST", "GET"])
@check_spotify
def album():
    log.debug("album request: data '{}', values: {}".format(flask.request.data,
                                                            flask.request.values.to_dict()))
    args = flask.request.get_json()

    if not args:
        args = flask.request.values.to_dict()

    a = __s.spotify.album_get(args)

    return flask.jsonify(a)

@__s.app.route("/login", methods=["POST", "GET"])
@check_spotify
def login():
    log.debug("login request: data '{}', values: {}".format(flask.request.data,
                                                            flask.request.values.to_dict()))
    args = flask.request.get_json()
    noadmin = flask.jsonify({"admin": False})

    if not args:
        args = flask.request.values.to_dict()

    if "id" not in args:
        log.warning("id missing in login request")
        return noadmin

    if args["id"] not in __s.get_user_admins():
        log.debug("id not admin: {}".format(args["id"]))
        return noadmin

    log.info("admin login: {}".format(args["id"]))

    return flask.jsonify({"admin": True})

@__s.app.route("/control/<action>", methods=["POST", "GET"])
@check_spotify
def control(action):
    log.debug("control request: action '{}', data '{}', values: {}".format(action,
                                                                           flask.request.data,
                                                                           flask.request.values.to_dict()))
    args = flask.request.get_json()
    noadmin = flask.jsonify({"admin": False})

    if not args:
        args = flask.request.values.to_dict()

    if "id" not in args:
        log.warning("id missing in login request")
        return noadmin

    if args["id"] not in __s.get_user_admins():
        log.debug("id not admin: {}".format(args["id"]))
        return noadmin

    a = __s.spotify.control(action, args)

    return flask.jsonify(a)
