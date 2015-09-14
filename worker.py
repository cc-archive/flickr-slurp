from __future__ import print_function

import flickrapi
import logging
import mysql.connector
from mysql.connector import errorcode
import socket
import sys
import yaml

import json

LOGLEVEL = 25

#NOTE: Pages are index base 1
#      Page count is inclusive, if there are 100 pages there's a page 100

#NOTE: methods beginning "fetch" access the Internet
#      methods beginning "insert" and "update" access the database

RESULTS_PER_PAGE = '500'
SEARCH_EXTRAS = 'license,original_format'

# Ignore so if we're restarting halfway through a page we just skip already
# inserted images from the previous run.
INSERT_PHOTO = \
"""INSERT IGNORE INTO photos (photo_id, license, nsid, farm, server,
                              originalsecret)
    VALUES (%(photo_id)s, %(license)s, %(nsid)s, %(farm)s, %(server)s,
            %(originalsecret)s);"""

UPDATE_PAGE_TOTAL = \
"""UPDATE shards SET page_total=%(page_total)s
    WHERE shard_id=%(shard_id)s;"""

UPDATE_PAGE_CURRENT = \
"""UPDATE shards SET page_current=%(page_current)s
    WHERE shard_id=%(shard_id)s;"""

SELECT_UNFINISHED_TASK = \
"""SELECT * FROM shards
    WHERE worker = %(my_hostname)s AND page_current < page_total
    LIMIT 1;"""

# This is actually a canonical use of LAST_INSERT_ID()
UPDATE_FRESH_TASK = \
"""UPDATE shards SET worker = %(my_hostname)s,
                     shard_id = LAST_INSERT_ID(shard_id)
    WHERE worker IS NULL
    LIMIT 1;"""
SELECT_FRESH_TASK = \
"""SELECT * FROM shards WHERE shard_id = LAST_INSERT_ID();"""

class Worker (object):

    def __init__(self, config):
        self.hostname = socket.gethostname()
        self.reset()
        flickrconfig = config['flickr']
        self.flickr = flickrapi.FlickrAPI(flickrconfig['api_key'],
                                          flickrconfig['api_secret'],
                                          format='parsed-json')
        dbconfig = config['database']
        self.connection = mysql.connector.connect(user=dbconfig['user'],
                                                  password=dbconfig['password'],
                                                  host=dbconfig['host'],
                                                  database=dbconfig['database'],
                                                  autocommit=True)
        self.cursor = self.connection.cursor()
        
    def reset(self):
        self.licence = ''
        self.characters = ''
        self.page_current = 1
        self.page_total = 0
        self.shard_id = -1

    def shutdown(self):
        self.cursor.close()
        self.connection.close()

    def insertPhoto(self, response):
        self.cursor.execute(INSERT_PHOTO,
                            {'photo_id': response['id'],
                             'license':response['license'],
                             'nsid':response['owner'],
                             'farm':response['farm'],
                             'server':response['server'],
                             'originalsecret':response['originalsecret']})
        
    def insertPhotos(self, response):
        for photo in response['photos']['photo']:
            self.insertPhoto(photo)

    def updateState(self):
        self.page_current += 1
        self.cursor.execute(UPDATE_PAGE_TOTAL,
                            {'shard_id':self.shard_id,
                             'page_total':self.page_total})
        self.cursor.execute(UPDATE_PAGE_CURRENT,
                            {'shard_id':self.shard_id,
                             'page_current':self.page_current})

    def fetchPhotosFromFlickr(self):
        response = self.flickr.photos.search(license=self.licence,
                                             page=self.page_current,
                                             per_page=RESULTS_PER_PAGE,
                                             extras=SEARCH_EXTRAS)
        # We do this here so it works both the first time (these need setting)
        # and if the details change (page_total increases for some reason)
        self.page_total = response['photos']['pages']
        self.page_current = response['photos']['page']
        logging.log(LOGLEVEL,
                    "Page {}{} {}/{}".format(self.characters,
                                             self.licence,
                                             self.page_current,
                                             self.page_total))
        return response

    def taskInProgress(self):
        return self.page_total == 0 or self.page_current <= self.page_total
    
    def runTask(self):
        while self.taskInProgress():
            response = self.fetchPhotosFromFlickr()
            self.insertPhotos(response)
            self.updateState()

    def configureFromTask(self, task):
        (shard_id, licence, characters, worker, page_total, page_current) = task
        self.shard_id = shard_id
        self.licence = licence
        self.characters = characters
        self.page_total = page_total
        self.page_current = page_current
            
    def selectUnfinishedTask(self):
        got_task = False
        self.cursor.execute(SELECT_UNFINISHED_TASK,
                            {'my_hostname':self.hostname})
        result = self.cursor.fetchone()
        if result is not None:
            got_task = True
            self.configureFromTask(result)
        return got_task
            
    def updateFreshTask(self):
        got_task = False
        self.cursor.execute(UPDATE_FRESH_TASK,
                            {'my_hostname':self.hostname})
        self.cursor.execute(SELECT_FRESH_TASK)
        result = self.cursor.fetchone()
        if result is not None:
            got_task = True
            self.configureFromTask(result)
        return got_task

    def logTask(self):
        logging.log(LOGLEVEL, "SHARD %s - %s%s",
                    self.shard_id, self.characters, self.licence)
        
    def go(self):
        logging.log(LOGLEVEL, 'Starting unfinished tasks.')
        while self.selectUnfinishedTask():
            self.logTask()
            self.runTask()
        logging.log(LOGLEVEL, 'Finished unfinished tasks.')
        logging.log(LOGLEVEL, 'Starting fresh tasks.')
        while self.updateFreshTask():
            self.logTask()
            self.runTask()
        logging.log(LOGLEVEL, 'Finished fresh tasks.')
        logging.log(LOGLEVEL, 'Shutting down.')
        self.shutdown()
        logging.log(LOGLEVEL, 'Shut down.')

if __name__ == '__main__':
    logging.basicConfig(level=LOGLEVEL)
    config = yaml.load(open('config.yaml'))
    worker = Worker(config)
    worker.go()
