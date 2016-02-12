from __future__ import print_function

import mysql.connector
from mysql.connector import errorcode
import yaml

# Dates are inclusive as per -
#    https://www.flickr.com/services/api/flickr.photos.search.html
# The second after the last image in the 100m image dataset
DATE_FROM = 1398683777
# 2016-02-14:00:00:00 GMT
DATE_TO = 1455408000
# Ten minute slices
DATE_STRIDE = 10 * 60

CREATES = [
"""
CREATE TABLE time_slices (
       time_slice_id INT        UNSIGNED NOT NULL PRIMARY KEY AUTO_INCREMENT,
       start_date   INT         UNSIGNED NOT NULL,
       end_date     INT         UNSIGNED NOT NULL,
       worker       VARCHAR(20),
       page_total   INT         NOT NULL DEFAULT 0,
       page_current INT         NOT NULL DEFAULT 1
);
""",
"""
-- We're not worried about url uniqueness as the results should be unique and
-- ordered by date.


CREATE TABLE flickr_photos_by_date (
       id           INT               UNSIGNED AUTO_INCREMENT PRIMARY KEY,
       photo_id     BIGINT            UNSIGNED UNIQUE NOT NULL,
       license      TINYINT           UNSIGNED NOT NULL,
       original_url VARCHAR(255)      NOT NULL,
       owner        VARCHAR(14)       NOT NULL,
       owner_name   VARCHAR(255)      NOT NULL,
       title        VARCHAR(255)      NOT NULL
);
""",
"""
CREATE INDEX photo_id_index on flickr_photos_by_date (photo_id);
"""
]

INSERT_SHARD = \
"""INSERT INTO time_slices (start_date, end_date)
    VALUES (%(start_date)s, %(end_date)s)"""

def create_tables (cursor):
    print("Creating:")
    for create in CREATES:
        try:
            cursor.execute(create)
        except mysql.connector.Error as err:
            if err.errno == errorcode.ER_TABLE_EXISTS_ERROR:
                print("already exists.")
            else:
                print(err.msg)
        else:
            print("OK")

def create_shards (cursor):
    print("Initializing time slices.")
    for start_date in xrange(DATE_FROM, DATE_TO, DATE_STRIDE):
        # - 1 as inclusive range
        end_date = start_date + DATE_STRIDE - 1
        cursor.execute(INSERT_SHARD,
                       {'start_date': start_date,
                        'end_date': end_date})

if __name__ == '__main__':
    config = yaml.load(open('config.yaml'))
    dbconfig = config['database']
    connection = mysql.connector.connect(user=dbconfig['user'],
                                         password=dbconfig['password'],
                                         host=dbconfig['host'],
                                         database=dbconfig['database'])
    cursor = connection.cursor()
    create_tables(cursor)
    create_shards(cursor)
    connection.commit()
    cursor.close()
    connection.close()
