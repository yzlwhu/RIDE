#  Copyright 2008-2012 Nokia Siemens Networks Oyj
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
from Queue import Queue
from threading import Thread
from robotide.spec.librarydatabase import LibraryDatabase
from robotide.spec.libraryfetcher import _get_import_result_from_process

class LibraryManager(Thread):

    def __init__(self, database_name):
        self._database_name = database_name
        self._messages = Queue()
        Thread.__init__(self)
        self.setDaemon(True)

    def run(self):
        self._initiate_database_connection()
        while True:
            if not self._handle_message():
                break
        self._database.close()

    def _initiate_database_connection(self):
        self._database = LibraryDatabase(self._database_name)

    def _handle_message(self):
        message = self._messages.get()
        if not message:
            return False
        type = message[0]
        if type == 'fetch':
            self._handle_fetch_keywords_message(message)
        return True

    def _handle_fetch_keywords_message(self, message):
        _, library_name, library_args, callback = message
        try:
            keywords = _get_import_result_from_process(library_name, library_args)
        except ImportError:
            keywords = []
        db_keywords = self._database.fetch_library_keywords(library_name, library_args)
        if not db_keywords or self._keywords_differ(keywords, db_keywords):
            self._database.insert_library_keywords(library_name, library_args, keywords)
            self._call(callback, keywords)
        else:
            self._database.update_library_timestamp(library_name, library_args)

    def _call(self, callback, *args):
        try:
            callback(*args)
        except Exception:
            pass

    def fetch_keywords(self, library_name, library_args, callback):
        self._messages.put(('fetch', library_name, library_args, callback))

    def stop(self):
        self._messages.put(False)

    def _keywords_differ(self, keywords1, keywords2):
        if keywords1 != keywords2 and None in (keywords1, keywords2):
            return True
        if len(keywords1) != len(keywords2):
            return True
        for k1, k2 in zip(keywords1, keywords2):
            if k1.name != k2.name:
                return True
            if k1.doc != k2.doc:
                return True
            if k1.arguments != k2.arguments:
                return True
            if k1.source != k2.source:
                return True
        return False
