# import_photos

Same as photos, but with only photo_id, original_url, accessed.

LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-0.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-1.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-2.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-3.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-4.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-5.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-6.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-7.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-8.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-9.tsv' INTO TABLE import_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';


# Add an index to PHOTOS (after "eek" below)

ALTER TABLE photos DROP PRIMARY KEY;
ALTER TABLE photos ADD id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY;
CREATE INDEX photos_photo_ids on photos (photo_id);


# numeric_id_photos

Same as import_photos, but with integer photo_id

We also need an integer id pk so we can query ranges efficiently.

Flickr ids won't fit in max mysql unsigned int,
Unsigned int max: 4294967295
Flickr id:        23738440462
So use unsigned bigint

Definition of table over time:

CREATE TABLE numeric_id_photos (
    photo_id     BIGINT        UNSIGNED NOT NULL PRIMARY KEY,
    original_url CHAR(255)     NOT NULL
);
ALTER TABLE numeric_id_photos DROP PRIMARY KEY;
ALTER TABLE numeric_id_photos ADD id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY;
CREATE INDEX numeric_id_photos_photo_ids on numeric_id_photos (photo_id);
ALTER TABLE numeric_id_photos ADD UNIQUE(photo_id);

LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-0.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-1.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-2.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-3.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-4.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-5.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-6.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-7.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-8.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';
LOAD DATA INFILE '/root/yfcc100m-for-import/yfcc100m_dataset-9.tsv' INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';


# yfcc100m

Example row:

6985418911      39089491@N00    nino63004       2012-02-16 09:56:37.0   1331840483      Canon+PowerShot+ELPH+310+HS     IMG_0520                canon,canon+powershot+hs+310,carnival+escatay,cruise,elph,hs+310,key+west+florida,powershot             -81.804885      24.550558       12      http://www.flickr.com/photos/39089491@N00/6985418911/   http://farm8.staticflickr.com/7205/6985418911_df7747990d.jpg    Attribution-NonCommercial-NoDerivs License      http://creativecommons.org/licenses/by-nc-nd/2.0/       7205    8       df7747990d      692d7e0a7f      jpg     0

The formatting uses neither tabs nor columns, and fields contain spaces.
So assume \s\s+ is the delimeter. Convert this to tab so cut works.

Column 1 (base 1) is photo id, 13 is original photo url. We can extract other data later

For some reason cut needs column 15.

sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-0 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-0.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-1 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-1.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-2 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-2.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-3 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-3.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-4 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-4.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-5 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-5.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-6 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-6.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-7 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-7.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-8 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-8.tsv
sed 's/ \{2,\}/\t/g' .presents/yfcc100m_dataset-9 | cut -f1,15 > yfcc100m-for-import/yfcc100m_dataset-9.tsv


# Add photo data

insert ignore into import_photos (photo_id, original_url) select photo_id, original_url from photos;


# Eeek!

A simple select of one row by id from import_photos takes 2 hours.

Rethink marking rows. Have a set stride and an index, and update those outside the table.


# Photo export to numeric id import

select photo_id, original_url into outfile '/tmp/photos_dump.tsv' FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n' from photos;

mv /tmp/photos_dump.tsv ~

// Ignore so we ignore duplicate indexes and don't crash.

LOAD DATA INFILE '/root/photos_dump.tsv' IGNORE INTO TABLE numeric_id_photos FIELDS TERMINATED BY '\t' LINES TERMINATED BY '\n';

This gives (with SHOW WARNINGS):

+---------+------+-------------------------------------------------+
| Level   | Code | Message                                         |
+---------+------+-------------------------------------------------+
| Warning | 1062 | Duplicate entry '10773813505' for key 'PRIMARY' |
| Warning | 1062 | Duplicate entry '11299042076' for key 'PRIMARY' |
| Warning | 1062 | Duplicate entry '12471324343' for key 'PRIMARY' |
| Warning | 1062 | Duplicate entry '2168916447' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '2168916697' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '2168917367' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '2169709212' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '2169709676' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '2169710068' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '3931248413' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '3931252207' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '3932015208' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '3932028964' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '3982493278' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '3984036532' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '4077726796' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5026899025' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5027516338' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5043849220' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5067427772' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5164894521' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5644713182' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '5673185472' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '6646059381' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '6677859921' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '7143462691' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '78574833' for key 'PRIMARY'    |
| Warning | 1062 | Duplicate entry '8222539434' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '8695998928' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '8850126582' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '8877660540' for key 'PRIMARY'  |
| Warning | 1062 | Duplicate entry '8883956325' for key 'PRIMARY'  |
+---------+------+-------------------------------------------------+

Which for half a million entries vs. 100 million isn't bad.







apt-get install rsync

# pgrep returns 0 for success, > 0 for failure, so we use logical and here:
# && doesn't work for some reason, use [ $? ... ] instead.

*/5 * * * * /bin/bash /root/tickler.sh


# Switch to a.o upload at:

here ->  95543501 | 48185 |




iaskeys:
export IAS3KEYS=XShiXQDWiHu2GcIB:pIdYikabnHybiGyW

Collection:
flickr-0cfdd119-0b17-4fbe-87cb-d3771617087f


Internet Archive...
login: ml@creativecommons.org
password: dec16

Upload README with contact information w/personal contact info:

Hello!
This is a backup of CC licensed images from flickr.
For more information, contact-
mattl@cc
rob@cc


# Date slice import

CREATE TABLE date_slice_photos (
       -- Photo IDs are unique across servers, so we use this as our key
       photo_id     VARCHAR(12)       NOT NULL PRIMARY KEY,
       license      TINYINT           UNSIGNED NOT NULL,
       original_url VARCHAR(255)      NOT NULL,
       owner        VARCHAR(14)       NOT NULL,
       owner_name   VARCHAR(255)      NOT NULL,
       title        VARCHAR(255)      NOT NULL,
       accessed     TIMESTAMP         NOT NULL DEFAULT CURRENT_TIMESTAMP,
       filepath     VARCHAR(255)
       );

ALTER TABLE date_slice_photos DROP PRIMARY KEY;
ALTER TABLE date_slice_photos ADD id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY;
CREATE INDEX date_slice_photos_photo_ids on date_slice_photos (photo_id);

load data infile '/tmp/flickr_photos_by_date_1.txt' into table date_slice_photos (photo_id, license, original_url, owner, owner_name, title);
