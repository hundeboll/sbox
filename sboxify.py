#!/usr/bin/env python2

import os
import yaml
import logging
import spotify
from threading import Event as event
from threading import Thread as thread

slog = logging.getLogger("spotify")
slog.setLevel(logging.INFO)

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())

class sboxify(object):
    event_logged_in = event()
    event_stop = event()

    def __init__(self, config):
        self.config = config
        self.session = spotify.Session()
        self.playlist = sboxify_playlist(self.session, config)
        self.player = sboxify_player(self.session, self.playlist, config)

    def stop(self):
        self.event_stop.set()
        self.thread.join()
        log.debug("stopped")

    def start(self):
        self.thread = thread(None, self.run, "sboxify")
        self.thread.start()
        log.debug("started")

    def run(self):
        self.login()
        self.loop = spotify.EventLoop(self.session)
        self.loop.start()

        while not self.event_stop.wait(.1):
            continue

        log.debug("done")

    def login(self):
        self.session.on(
                spotify.SessionEvent.CONNECTION_STATE_UPDATED,
                self.on_logged_in)
        user = self.config.spotify_user
        passwd = self.config.spotify_pass
        self.session.login(user, passwd)

    def is_logged_in(self):
        return self.event_logged_in.is_set()

    def on_logged_in(self, session):
        if not self.session.connection.state is spotify.ConnectionState.LOGGED_IN:
            return

        self.event_logged_in.set()
        log.debug("logged in")
        self.playlist.handle_logged_in()
        self.player.handle_logged_in()

    def search(self, query):
        if not 'q' in query:
            log.warning("search query did not contain a q element: {}".format(query))
            return {"error": "specify search query as 'q'"}

        search = sboxify_search(self.session, **query)

        return search.result()

    def playlist_add(self, query):
        if not "key" in query:
            log.warning("add query did not contain a 'key' element: {}".format(query))
            return {"error": "specify key in query"}

        if not "id" in query:
            log.warning("add query did not contain a 'id' element: {}".format(query))
            return {"error": "specify id in query"}

        uri = query["key"]
        user_id = query["id"]

        return self.playlist.add_track(uri, user_id)

    def playlist_remove(self, query):
        if not "key" in query:
            log.warning("add query did not contain a 'key' element: {}".format(query))
            return {"error": "specify key in query"}

        if not "id" in query:
            log.warning("add query did not contain a 'id' element: {}".format(query))
            return {"error": "specify id in query"}

        uri = query["key"]
        user_id = query["id"]

        return self.playlist.remove_track(uri, user_id)


    def playlist_get(self, query):
        data = {}
        data["tracks"] = self.playlist.get_tracks()

        if "id" in query:
            data["user_tracks"] = self.playlist.get_user_tracks(query["id"])

        return data

    def artist_get(self, query):
        if not "key" in query:
            log.warning("add query did not contain a 'key' element: {}".format(query))
            return {"error": "specify key in query"}

        uri = query["key"]
        artist = self.session.get_artist(uri)
        browser = artist.browse().load()

        out = {
                "albums": sboxify_dictify.albums(browser.albums),
                "tracks": sboxify_dictify.tracks(browser.tracks),
            }

        return out

    def album_get(self, query):
        if not "key" in query:
            log.warning("add query did not contain a 'key' element: {}".format(query))
            return {"error": "specify key in query"}

        uri = query["key"]
        album = self.session.get_album(uri)
        browser = album.browse().load()

        out = {
                "tracks": sboxify_dictify.tracks(browser.tracks),
            }

        return out

    def control(self, action, query):
        if action == "pause":
            self.player.toggle_pause()
            return {"control": True, "action": action}

        if action == "next":
            self.player.play_next()
            return {"control": True, "action": action}

        if action == "prev":
            self.player.play_prev()
            return {"control": True, "action": action}

        return {"control": False, "action": action}

class sboxify_dictify(object):
    @staticmethod
    def track_props(track):
        track.load()
        image = track.album.cover()

        if image:
            image = image.load().link.url

        props = {
                "key": track.link.uri,
                "album": (track.album.link.uri, track.album.load().name),
                "artists": [(artist.link.uri, artist.load().name) for artist in track.artists],
                "duration": track.duration,
                "name": track.name,
                "popularity": track.popularity,
                "image": image,
                }

        return props

    @staticmethod
    def tracks(tracks):
        out = []

        for track in tracks:
            props = sboxify_dictify.track_props(track)
            out.append(props)

        return out

    @staticmethod
    def album_props(album):
        album.load()
        image = album.cover()

        if image:
            image = image.load().link.url

        props = {
                "key": album.link.uri,
                "artist": album.artist.load().name,
                "year": album.year,
                "type": album.type,
                "name": album.name,
                "image": image,
                }

        return props

    @staticmethod
    def albums(albums):
        out = []

        for album in albums:
            props = sboxify_dictify.album_props(album)
            out.append(props)

        return out

    @staticmethod
    def artist_props(artist):
        artist.load()
        image = artist.portrait()

        if image:
            image = image.load().link.url

        props = {
                "key": artist.link.uri,
                "name": artist.name,
                "image": image,
                }

        return props

    @staticmethod
    def artists(artists):
        out = []

        for artist in artists:
            props = sboxify_dictify.artist_props(artist)
            out.append(props)

        return out

class sboxify_search(object):
    def __init__(self, session, q, **kwargs):
        self.kwargs = kwargs
        self.search = session.search(q, search_type=spotify.SearchType.SUGGEST)
        self.search.load()

    def result(self):
        result = {}

        if "noalbums" not in self.kwargs:
            result["albums"] = self.albums()

        if "noartists" not in self.kwargs:
            result["artists"] = self.artists()

        if "notracks" not in self.kwargs:
            result["tracks"] = self.tracks()

        return result

    def tracks(self):
        return sboxify_dictify.tracks(self.search.tracks)

    def albums(self):
        return sboxify_dictify.albums(self.search.albums)

    def artists(self):
        return sboxify_dictify.artists(self.search.artists)

class sboxify_playlist(object):
    def __init__(self, session, config):
        self.session = session
        self.config = config
        self.index = config.spotify_index

    def handle_logged_in(self):
        if not self.get_playlist():
            self.create_playlist()

        self.load_user_tracks()

    def load_user_tracks(self):
        if not os.path.exists(self.config.user_list):
            self.users = []
        else:
            self.users = yaml.load(open(self.config.user_list))

        user_tracks_len = len(self.users)
        playlist_len = len(self.playlist.tracks)

        if user_tracks_len != playlist_len:
            log.warning("user_tracks mismatch, resetting... " +
                        "(user_tracks={}, playlist={})".format(user_tracks_len, playlist_len))
            self.users = ["unknown_user"] * playlist_len
            yaml.dump(self.users, open(self.config.user_list, 'w'))

    def get_playlist(self):
        info = self.config.spotify_playlist
        config_uri = info["uri"]
        config_name = info["name"]

        if not config_uri:
            return False

        self.playlist = self.session.get_playlist(config_uri)
        spotify_name = self.playlist.load().name
        log.info("loaded playlist: {} ({})".format(config_name, config_uri))

        if not spotify_name == config_name:
            log.warning("configured playlist name ({}) does not match" + 
                        "spotify playlist name ({})".format(spotify, config_name))

        if self.index >= len(self.playlist.tracks):
            log.warning("configured index ({}) is greater".format(self.index) +
                        "than playlist len ({}); resetting...".format(len(self.playlist.tracks)))
            self.index = 0
            self.config.spotify_index = self.index

        return True

    def create_playlist(self):
        info = self.config.spotify_playlist
        name = info["name"]

        self.playlist = self.session.playlist_container.add_new_playlist(name)
        uri = self.playlist.link.uri
        info["uri"] = uri
        self.config.spotify_playlist = info
        log.info("created new playlist: {} ({})".format(self.playlist.name, uri))

    def get_tracks(self):
        tracks = sboxify_dictify.tracks(self.playlist.tracks[self.index:])

        return tracks

    def get_user_tracks(self, user_id):
        out = []
        tracks = self.playlist.tracks[self.index:]

        for idx,user in enumerate(self.users[self.index:]):
            if user != user_id:
                continue

            out.append(tracks[idx])

        return sboxify_dictify.tracks(out)

    def add_track(self, key, user_id):
        users = []
        offset = 0

        while not users:
            index = self.index + offset

            for idx,user in enumerate(self.users[index:]):
                if user in users:
                    break

                users.append(user)

            offset += idx

            if user_id not in users:
                break

            users = []

        log.debug("index: {}".format(offset))

        track = spotify.Track(self.session, uri=key)
        self.playlist.add_tracks(track)
        self.add_user_track(user_id)

        return sboxify_dictify.track_props(track)

    def add_user_track(self, user_id):
        self.users.append(user_id)
        yaml.dump(self.users, open(self.config.user_list, 'w'))

    def remove_track(self, key, user_id):
        for idx,track in enumerate(self.playlist.tracks):
            if track.load().link.uri != key:
                continue

            if self.users[idx] != user_id:
                continue

            self.playlist.remove_tracks(idx)
            self.remove_user_track(idx)
            return sboxify_dictify.track_props(track)

        return {"error": "track not found for user id"}

    def remove_user_track(self, idx):
        del self.users[idx]
        yaml.dump(self.users, open(self.config.user_list, 'w'))

    def get_next_track(self):
        self.index = (self.index + 1) % len(self.playlist.tracks)
        self.config.spotify_index = self.index
        return self.playlist.tracks[self.index].load()

    def get_prev_track(self):
        self.index = (self.index - 1) % len(self.playlist.tracks) 
        self.config.spotify_index = self.index
        return self.playlist.tracks[self.index].load()

class sboxify_player(object):
    def __init__(self, session, playlist, config):
        self.session = session
        self.playlist = playlist
        self.audio = spotify.AlsaSink(session)
        self.config = config

        session.on(spotify.SessionEvent.END_OF_TRACK, self.on_end_of_track)

    def is_playing(self):
        return self.session.player.state == spotify.player.PlayerState.PLAYING

    def is_paused(self):
        return self.session.player.state == spotify.player.PlayerState.PAUSED

    def is_loaded(self):
        return self.session.player.state == spotify.player.PlayerState.LOADED

    def play_track(self, track):
        try:
            log.info("playing next track: {}, artist: {}, album: {}".format(track.name,
                                                                            track.artists[0].load().name,
                                                                            track.album.load().name))
        except UnicodeEncodeError as e:
            log.error(e)

        self.session.player.load(track)
        self.session.player.play()

    def play_next(self):
        track = self.playlist.get_next_track()
        self.play_track(track)

    def play_prev(self):
        track = self.playlist.get_prev_track()
        self.play_track(track)

    def on_end_of_track(self, session):
        self.play_next()

    def handle_logged_in(self):
        self.play_next()

    def toggle_pause(self):
        if not self.is_playing():
            self.play()
        else:
            self.pause()

    def play(self):
        if self.is_paused():
            self.session.player.play()
        elif not self.is_loaded():
            self.play_next()

    def pause(self):
        self.session.player.pause()
