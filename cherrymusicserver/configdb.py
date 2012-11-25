#!/usr/bin/python3
#
# CherryMusic - a standalone music server
# Copyright (c) 2012 Tom Wallroth & Tilman Boerner
#
# Project page:
#   http://fomori.org/cherrymusic/
# Sources on github:
#   http://github.com/devsnd/cherrymusic/
#
# CherryMusic is based on
#   jPlayer (GPL/MIT license) http://www.jplayer.org/
#   CherryPy (BSD license) http://www.cherrypy.org/
#
# licensed under GNU GPL version 3 (or later)
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
#

import os
import sqlite3

from cherrymusicserver.configuration import Configuration, Property
from cherrymusicserver import configuration
from cherrymusicserver import log

class ConfigDB(object):
    """quick and dirty implementation of a config database in sqlite3"""

    def __init__(self, CONFIGDBFILE):
        setupDB = not os.path.isfile(CONFIGDBFILE) or os.path.getsize(CONFIGDBFILE) == 0
        self.conn = sqlite3.connect(CONFIGDBFILE, check_same_thread=False)

        if setupDB:
            log.i('Creating config db table...')
            self.conn.execute(
                              'CREATE TABLE config ('
                              'key text UNIQUE, '
                              'value text, '
                              'type text, '
                              'validity text, '
                              'readonly int, '
                              'hidden int, '
                              'desc text'
                              ')'
                              )
            self.conn.execute('CREATE INDEX idx_config ON config(key)')
            log.i('done.')
            log.i('Initializing config db with default configuration...')
            self.reset_to_default()
            log.i('done.')
            log.i('Connected to Database. (' + CONFIGDBFILE + ')')

    def load(self):
        cursor = self.conn.execute('SELECT key, value, type, validity, readonly, hidden, desc'
                                   ' FROM config')
        with configuration.create() as cfg:
            while True:
                row = cursor.fetchone()
                if row is None:
                    break
                cfg += Property(*row)
        return cfg

    def save(self, cfg, clear=False):
        """save cfg to database. clear==True replaces existing config completely. clear=False behaves like update."""
        if clear:
            self.conn.execute('DELETE FROM config')
            self._dump(cfg)
        else:
            self.update(cfg)

    def update(self, cfg):
        """updates config database from cfg. entries in cfg overwrite existing keys or are created new.
        existing entries not in cfg remain untouched."""
        if cfg:
            for prop in configuration.to_list(cfg):
                foundid = self.conn.execute('SELECT rowid FROM config'
                                            ' WHERE key=?', (prop.name,)
                                            ).fetchone()
                if foundid is None:
                    self._insert_property(prop)
                else:
                    foundid = foundid[0]
                    self._update_property(foundid, prop)
            self.conn.commit()

    def reset_to_default(self):
        '''clears all content from the database and reinitializes it with default values'''
        self.save(configuration.from_defaults(), clear=True)

    def _dump(self, cfg):
        if cfg:
            for proptuple in configuration.to_list(cfg):
                self._insert_property(proptuple)
            self.conn.commit()

    def _insert_property(self, prop):
        self.conn.execute('INSERT INTO config'
                          ' (key, value, type, validity, readonly, hidden, desc) '
                          'VALUES (?,?,?,?,?,?,?)', prop)

    def _update_property(self, pid, prop):
        args = prop + (pid,)
        self.conn.execute('UPDATE config SET'
                          ' key=?, value=?, type=?, validity=?, readonly=?, hidden=?, desc=?'
                          ' WHERE rowid=?', args)
