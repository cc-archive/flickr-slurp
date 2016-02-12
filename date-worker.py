import flickrapi
import logging, time
import mysql.connector
from mysql.connector import errorcode
import yaml

# This is the program that fetches data from flickr and saves it to the db.
# It finds shards that no other instances of this program are downloading
# then gets the matching results from the flickr api and inserts them.
# It handles errors a little but do watch the logs.

# 3600 API calls per hour = 1 per second
API_HIT_TIME = 1 * 1001

LOGLEVEL = 25

MAX_TRIES = 10

# Time (seconds) to sleep while waiting to retry. Make it relatively large.
SLEEP_TIME = 60

LICENSES = '1,2,3,4,5,6,7,8'

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
"""INSERT IGNORE INTO flickr_photos_by_date (photo_id, license, original_url,
                                             owner, owner_name, title)
    VALUES (%(photo_id)s, %(license)s, %(original_url)s,
            %(owner)s, %(owner_name)s, %(title)s);"""

UPDATE_PAGE_TOTAL = \
"""UPDATE time_slices SET page_total=%(page_total)s
    WHERE time_slice_id=%(time_slice_id)s;"""

UPDATE_PAGE_CURRENT = \
"""UPDATE time_slices SET page_current=%(page_current)s
    WHERE time_slice_id=%(time_slice_id)s;"""

SELECT_UNFINISHED_TASK = \
"""SELECT * FROM time_slices
    WHERE worker = %(my_identifier)s AND page_current < page_total
    LIMIT 1;"""

# This is actually a canonical use of LAST_INSERT_ID()
UPDATE_FRESH_TASK = \
"""UPDATE time_slices SET worker = %(my_identifier)s,
                     time_slice_id = LAST_INSERT_ID(time_slice_id)
    WHERE worker IS NULL
    LIMIT 1;"""

SELECT_FRESH_TASK = \
"""SELECT * FROM time_slices WHERE time_slice_id = LAST_INSERT_ID();"""

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
        self.start_date = 0
        self.end_date = 0
        self.page_current = 1
        self.page_total = 0
        self.time_slice_id = -1

    def shutdown(self):
        self.cursor.close()
        self.connection.close()

    def insertPhoto(self, response):
        # There will be no url_o if the user has disabled downloading of their
        # photos, so only store the photo if there's a url_o .
        # We could catch the exception but this is clearer.
        if 'url_o' in response.keys():
            self.cursor.execute(INSERT_PHOTO,
                                {'photo_id':response['id'],
                                 'license':int(response['license']),
                                 'original_url':response['url_o'],
                                 'owner':response['owner'],
                                 'owner_name':response['ownername'],
                                 'title':response['title']})
        #else:
        #    logging.error("No url_o in %s, not inserting." % response['id'])

    def insertPhotos(self, response):
        for photo in response['photos']['photo']:
            self.insertPhoto(photo)

    def updateState(self):
        self.page_current += 1
        self.cursor.execute(UPDATE_PAGE_TOTAL,
                            {'time_slice_id':self.time_slice_id,
                             'page_total':self.page_total})
        self.cursor.execute(UPDATE_PAGE_CURRENT,
                            {'time_slice_id':self.time_slice_id,
                             'page_current':self.page_current})

    def fetchPhotosFromFlickr(self):
        response = self.flickr.photos.search(min_upload_date=self.start_date,
                                             max_upload_date=self.end_date,
                                             license=LICENSES,
                                             page=self.page_current,
                                             per_page=RESULTS_PER_PAGE,
                                             extras=SEARCH_EXTRAS)
        # We do this here so it works both the first time (these need setting)
        # and if the details change (page_total increases for some reason)
        self.page_total = response['photos']['pages']
        self.page_current = response['photos']['page']
        logging.log(LOGLEVEL,
                    "TIME_SLICE {} - Page {}/{}".format(self.time_slice_id,
                                                        self.page_current,
                                                        self.page_total)),
        return response

    def taskInProgress(self):
        return self.page_total == 0 or self.page_current <= self.page_total

    def runTask(self, tries=0):
        while self.taskInProgress():
            try:
                started_at = int(round(time.time() * 1000))
                response = self.fetchPhotosFromFlickr()
                self.insertPhotos(response)
                self.updateState()
                ended_at = int(round(time.time() * 1000))
                # Make sure we don't call the API too often
                execution_time = ended_at - started_at
                if execution_time < API_HIT_TIME:
                    time.sleep((API_HIT_TIME - execution_time) / 1000.0)
            except Exception, e:
                logging.error(e)
                time.sleep(SLEEP_TIME)
                if tries < MAX_TRIES:
                    logging.info("Retrying %s - %s", self.time_slice_id, e)
                    self.runTask(tries + 1)
                else:
                    self.page_current = self.page_total + 1
                    self.updateState()
                    logging.error("Giving up on %s - %s", self.time_slice_id, e)

    def configureFromTask(self, task):
        (time_slice_id, start_date, end_date, worker, page_total,
         page_current) = task
        self.time_slice_id = time_slice_id
        self.start_date = start_date
        self.end_date = end_date
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
        logging.log(LOGLEVEL, "TIME_SLICE %s - %s -- %s",
                    self.time_slice_id, self.start_date, self.end_date)

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
