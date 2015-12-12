import sys, urlparse
import mysql.connector
from mysql.connector import errorcode
import yaml

# This is the program that downloads the original images for database entries.
# It finds un-downloaded images in the database then downloads them from flickr.

PHOTO_COUNT = 10000

PHOTO_PHOTO_ID = 0
PHOTO_ORIGINAL_URL = 1

PAD_DIR_TO = 10

SELECT_PHOTOS = \
"""SELECT photo_id, original_url FROM photos
    LIMIT %(count)s
    OFFSET %(offset)s;"""

class WGetGen (object):

    def __init__(self, config, offset, count):
        self.row_offset = offset
        self.row_count = count
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

    def selectPhotos(self):
        self.cursor.execute(SELECT_PHOTOS,
                            {'offset':self.row_offset,
                             'count':self.row_count})

    def directoryPath(self, photo_id):
        path_padded = ('0' * (PAD_DIR_TO - len(photo_id))) + photo_id
        return self.download_dir + ('/'.join(list(path_padded)))

    def writeCommands(self, photo_id, photo_url):
        filename = (urlparse.urlparse(photo_url).path).split('/')[-1]
        path = self.directoryPath(photo_id)
        filepath = path + '/' + filename
        print 'mkdir -p ' + path
        print 'wget --debug ' + photo_url + ' -O ' + filepath

    def go(self):
        self.selectPhotos()
        for photo in self.cursor:
            self.writeCommands(photo[PHOTO_PHOTO_ID], photo[PHOTO_ORIGINAL_URL])

def cli():
    if len(sys.argv) != 2:
        print "Usage: python wgetget.py <OFFSET>"
        sys.exit(1)
    return int(sys.argv[1])

if __name__ == '__main__':
    offset = cli()
    config = yaml.load(open('config.yaml'))
    downloader = WGetGen(config, offset, PHOTO_COUNT)
    downloader.go()
