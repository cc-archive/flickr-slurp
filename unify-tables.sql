CREATE TABLE `flickr_photos_unified` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT PRIMARY KEY,
  `photo_id` bigint(20) unsigned NOT NULL,
  `license` tinyint(3) unsigned NOT NULL,
  `original_url` varchar(255) NOT NULL,
  `owner` varchar(14) NOT NULL,
  `owner_name` varchar(255) NOT NULL,
  `title` varchar(255) NOT NULL
);
CREATE INDEX flickr_photos_unified_photo_ids on flickr_photos_unified (photo_id);

INSERT INTO flickr_photos_unified (photo_id, license, original_url, owner, owner_name, title) SELECT photo_id, license, original_url, owner, owner_name, title FROM flickr_photos_by_date;
INSERT IGNORE INTO flickr_photos_unified (photo_id, license, original_url, owner, owner_name, title) SELECT photo_id, license, original_url, owner, owner_name, title FROM flickr_photos_by_date_1;
INSERT IGNORE INTO flickr_photos_unified (photo_id, license, original_url, owner, owner_name, title) SELECT photo_id, license, original_url, owner, owner_name, title FROM date_slice_photos;
INSERT IGNORE INTO flickr_photos_unified (photo_id, license, original_url, owner, owner_name, title) SELECT photo_id, license, original_url, owner, owner_name, title FROM flickr_photos_from_queries;
