import logging, os, urllib, urlparse
import mysql.connector
from mysql.connector import errorcode
import yaml

# This is the program that downloads the original images for database entries.
# It finds un-downloaded images in the database then downloads them from flickr.

PHOTO_PHOTO_ID = 0
PHOTO_ORIGINAL_URL = 2

LOGLEVEL = 25

PAD_DIR_TO = 10

NO_ERROR = 0
DOWNLOAD_ERROR = 1
WRITE_ERROR = 2

SELECT_UNFINISHED_TASK = \
"""SELECT * FROM downloads
    WHERE downloader = %(my_identifier)s
     AND status = -1
    LIMIT 1;"""

# LEFT JOIN...IS NULL is alleged to be faster than NOT EXISTS on MySQL
SELECT_FRESH_TASK = \
"""SELECT * FROM photos
    LEFT JOIN downloads ON photos.photo_id = downloads.photo_id
    WHERE downloads.photo_id IS NULL
    LIMIT 1;"""

# This will fail if someone else slipped in
INSERT_FRESH_TASK = \
"""INSERT downloads (photo_id, downloader)
    VALUES (%(photo_id)s, %(my_identifier)s);"""

UPDATE_TASK_STATUS = \
"""UPDATE downloads SET status = %(status)s
    WHERE photo_id = %(photo_id)s
"""

SELECT_PHOTO_URL = \
"""SELECT original_url FROM photos
    WHERE photo_id = %(photo_id)s
"""

UPDATE_PHOTO_FILEPATH = \
"""UPDATE photos SET filepath = %(filepath)s
    WHERE photo_id = %(photo_id)s
"""

class Downloader (object):

    def __init__(self, config):
        self.identifier = config['worker']['id']
        self.reset()
        self.download_dir = config['worker']['download_dir']
        if self.download_dir[-1] != '/':
            self.download_dir += '/'
        dbconfig = config['database']
        self.connection = mysql.connector.connect(user=dbconfig['user'],
                                                  password=dbconfig['password'],
                                                  host=dbconfig['host'],
                                                  database=dbconfig['database'],
                                                  autocommit=True)
        self.cursor = self.connection.cursor()

    def reset(self):
        self.photo_id = False
        self.photo_url = False
        self.photo_filepath = False

    def shutdown(self):
        self.cursor.close()
        self.connection.close()

    def selectPhotoUrl(self, photo_id):
        photo_url = False
        self.cursor.execute(SELECT_PHOTO_URL, {'photo_id':photo_id})
        photo = self.cursor.fetchone()
        if photo is not None:
            photo_url = photo[0]
        return photo_url

    def fetchPhoto(self):
        state = DOWNLOAD_ERROR
        try:
            f = urllib.urlopen(self.photo_url)
            data = f.read()
            f.close()
            state = NO_ERROR
        except IOError, e:
            logging.error("Error opening url %s - %s", self.photo_url, e)
        return (state, data)

    def writePhoto(self, data):
        filename = (urlparse.urlparse(self.photo_url).path).split('/')[-1]
        path = self.directoryPath()
        self.ensureDirectoryPath(path)
        self.photo_filepath = path + '/' + filename
        try:
            with open(self.photo_filepath, 'w') as outfile:
                outfile.write(data)
                self.updatePhotoPath()
                state = NO_ERROR
        except IOError, e:
            state = WRITE_ERROR
        return state

    def directoryPath(self):
        path_padded = ('0' * (PAD_DIR_TO - len(self.photo_id))) + self.photo_id
        return self.download_dir + ('/'.join(list(path_padded)))

    def ensureDirectoryPath(self, path):
        try:
            os.makedirs(path)
        except OSError:
            pass

    def updatePhotoPath(self):
        self.cursor.execute(UPDATE_PHOTO_FILEPATH,
                            {'photo_id':self.photo_id,
                             'filepath':self.photo_filepath})

    def updateState(self, status):
        self.cursor.execute(UPDATE_TASK_STATUS,
                            {'photo_id':self.photo_id,
                             'status':status})

    def runTask(self):
        (state, photo) = self.fetchPhoto()
        if photo:
            state = self.writePhoto(photo)
        self.updateState(state)

    def configureFromDetails(self, photo_id, photo_url):
        self.photo_id = photo_id
        self.photo_url = photo_url

    def configureFromPhoto(self, task):
        photo_id = task[PHOTO_PHOTO_ID]
        photo_url = task[PHOTO_ORIGINAL_URL]
        self.configureFromDetails(photo_id, photo_url)

    def configureFromDownload(self, task):
        (photo_id, downloader, status, started) = task
        photo_url = self.selectPhotoUrl(photo_id)
        self.configureFromDetails(photo_id, photo_url)

    def selectUnfinishedTask(self):
        got_task = False
        self.cursor.execute(SELECT_UNFINISHED_TASK,
                            {'my_identifier':self.identifier})
        result = self.cursor.fetchone()
        if result is not None:
            got_task = True
            self.configureFromDownload(result)
        return got_task

    def insertFreshTask(self):
        got_task = False
        while got_task == False:
            try:
                self.cursor.execute(SELECT_FRESH_TASK)
                photo = self.cursor.fetchone()
                if photo is not None:
                    photo_id = photo[0]
                    self.cursor.execute(INSERT_FRESH_TASK,
                                        {'photo_id':photo_id,
                                         'my_identifier':self.identifier})
                    # If the execute tried to insert an existing photo_id
                    # we won't reach this code
                    got_task = True
                    self.configureFromPhoto(photo)
            except mysql.connector.IntegrityError as err:
                # Someone else slipped in before us, so just try again
                pass
        return got_task

    def logTask(self):
        logging.log(LOGLEVEL, "photo_id %s - %s", self.photo_id, self.photo_url)

    def go(self):
        logging.log(LOGLEVEL, 'Starting unfinished tasks.')
        while self.selectUnfinishedTask():
            self.logTask()
            self.runTask()
        logging.log(LOGLEVEL, 'Finished unfinished tasks.')
        logging.log(LOGLEVEL, 'Starting fresh tasks.')
        while self.insertFreshTask():
            self.logTask()
            self.runTask()
        logging.log(LOGLEVEL, 'Finished fresh tasks.')
        logging.log(LOGLEVEL, 'Shutting down.')
        self.shutdown()
        logging.log(LOGLEVEL, 'Shut down.')

if __name__ == '__main__':
    logging.basicConfig(level=LOGLEVEL)
    config = yaml.load(open('config.yaml'))
    downloader = Downloader(config)
    downloader.go()
