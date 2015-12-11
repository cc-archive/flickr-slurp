import flickrapi
import logging, time
import mysql.connector
from mysql.connector import errorcode
import yaml

# This is the program that fetches data from flickr and saves it to the db.
# It finds shards that no other instances of this program are downloading
# then gets the matching results from the flickr api and inserts them.
# It handles errors a little but do watch the logs.

LOGLEVEL = 25

MAX_TRIES = 10

# Time (seconds) to sleep while waiting to retry. Make it relatively large.
SLEEP_TIME = 60

#NOTE: Pages are index base 1
#      Page count is inclusive, if there are 100 pages there's a page 100

#NOTE: methods beginning "fetch" access the Internet
#      methods beginning "insert" and "update" access the database

RESULTS_PER_PAGE = '500'
SEARCH_EXTRAS = 'license,url_o,owner_name'

# Ignore so if we're restarting halfway through a page we just skip already
# inserted images from the previous run, or for photos returned by multiple
# searches.
INSERT_PHOTO = \
"""INSERT IGNORE INTO photos (photo_id, license, original_url, owner,
                              owner_name, title)
    VALUES (%(photo_id)s, %(license)s, %(original_url)s,
            %(owner)s, %(owner_name)s, %(title)s);"""

UPDATE_PAGE_TOTAL = \
"""UPDATE shards SET page_total=%(page_total)s
    WHERE shard_id=%(shard_id)s;"""

UPDATE_PAGE_CURRENT = \
"""UPDATE shards SET page_current=%(page_current)s
    WHERE shard_id=%(shard_id)s;"""

SELECT_UNFINISHED_TASK = \
"""SELECT * FROM shards
    WHERE worker = %(my_identifier)s AND page_current < page_total
    LIMIT 1;"""

# This is actually a canonical use of LAST_INSERT_ID()
UPDATE_FRESH_TASK = \
"""UPDATE shards SET worker = %(my_identifier)s,
                     shard_id = LAST_INSERT_ID(shard_id)
    WHERE worker IS NULL
    LIMIT 1;"""

SELECT_FRESH_TASK = \
"""SELECT * FROM shards WHERE shard_id = LAST_INSERT_ID();"""

class Worker (object):

    def __init__(self, config):
        self.identifier = config['worker']['id']
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
                            {'photo_id':response['id'],
                             'license':int(response['license']),
                             'original_url':response['url_o'],
                             'owner':response['owner'],
                             'owner_name':response['ownername'],
                             'title':response['title']})

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

    def runTask(self, tries=0):
        while self.taskInProgress():
            try:
                response = self.fetchPhotosFromFlickr()
                self.insertPhotos(response)
                self.updateState()
            except Exception, e:
                # e.g. KeyError: 'url_o'
                time.sleep(SLEEP_TIME)
                if tries < MAX_TRIES:
                    logging.info("Retrying %s - %s", self.shard_id, e)
                    self.runTask(tries + 1)
                else:
                    logging.error("Giving up on %s - %s", self.shard_id, e)

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
                            {'my_identifier':self.identifier})
        result = self.cursor.fetchone()
        if result is not None:
            got_task = True
            self.configureFromTask(result)
        return got_task

    def updateFreshTask(self):
        got_task = False
        self.cursor.execute(UPDATE_FRESH_TASK,
                            {'my_identifier':self.identifier})
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
