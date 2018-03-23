System Structure
================

We have a database server, an rsync server, and a number of small virtual machines.

The small virtual machines run a script that accesses the database server via a PHP script in order to fetch a list of flickr image URLs. The script then downloads them and transfers them to the rsync server.

The rsync server is where images are copied to once they are downloaded. It has an ssh key that the small virtual machines all use to access it. They fetch this key from the Apache instance running on the database server.

The database server runs a MySQL instance that holds the details of the images on flickr that we are downloading. It also runs processes to access the flickr API and insert the results into the database. And it services the small virtual machines via http using Apache, providing them with configuration information, lists of flickr image URLs to download, and the ssh key to use to connect to the rsync server.


Building The Database
=====================

Data Sources
------------

Our initial database was the flickr 100 million image database.

We have supplemented this with data gained by scripts that access the flickr API methodically:

1. A script that accesses the API searching for images in ten minute slices since 2004. This is intended to provide full coverage of the flickr database

2. A script that accesses the API searching for matches for search terms entered at search.creativecommons.org . This is intended to provide well-prioritised coverage of the flickr database.

In each case we fetch only Creative Commons-licensed image data. And we only fetch the data we need to provide attribution under the license, not any additional description or tag data.

API Search Scripts
------------------

The API search scripts are written in Python and are designed to be deployed on a cluster of machines, although we have only tested them on a single one. Each machine will need a separate flickr API key.

We use a script to create and populate a database table containing the details for individual searches of the API to be performed by the API search script. For example, a date range, a range of letters, a query string, and one or more license ID specifiers.

The worker scripts then fetch search details from the database, query the API, and save the results of the search in the database. Each worker marks the row that it is currently working on, to avoid another worker duplicating the search and to allow it to restard if interrupted. When the worker has finished storing the search details it marks the search task row as completed.

When there are no more searches left to perform, the worker script exits.

Search tasks are called "shards" in the code. This is a confusing name and should be changed.

Data Reconciliation
-------------------

Each script (e.g. time slice, search terms) saves its results to a separate database table.

After a run of the script is complete, we insert just the details required by the image URL vending script into the table used by that.

We need to combine the 100 million database and the API search databases into a single database containing all the details we have for each.


Image Downloading
=================

The Database Server
-------------------

The database server is running a MySQL instance containing several databases holding information about images on flickr and the progress of processes accessing the flickr API or downloading images from flickr.

The database server machine is also running an Apache web server that services the small virtual machines running the image downloader client script.

The web server runs a PHP script that vends image URLs to clients that request them. It keeps track of which URLs have been passed to clients using a simple offset count in a table in the database. when no more URLs are available it returns an empty list.

The web server also vends the image downloader client script, its configuration, and the SSH key it uses to communicate with the rsync server. This is obviously insecure and should be improved.

We have a dummy version of the PHP image URL vending script that we can replace the real one with temporarily. It just returns an empty list, which causes the clients to shut down until restarted by cron. This effectively puts them into maintenance mode.

Image Downloader Client
-----------------------

On a small virtual machine (a Digital Ocean "Droplet"), a Bash shell script requests a list of image URLs to download from the PHP script on the database server. It caches this list in a local file in case it needs to restart after errors. Then it uses wget to fetch the images, batched in parallel requests. When all the images in the list requested from the PHP script have been fetched from flickr they are sent to the rsync server. Finally the script cleans up the URL cache file and the downloaded images before starting again.

The script will download updated configuration information and updated versions of itself from the server if it exits. It is restarted by a cron script every two minutes to protect against crashes.

When the script fetches an empty list from the database server it stops (although the cron task will restart it).

Setting Up The Clients
----------------------

We created a Digital Ocean "Droplet" small virtual machine, installed and configured the downloader client script on it, then after testing we created an image from that.

We then put the maintenance mode script into effect on the database server, made more virtual machines from the image, and turned off maintenance mode. This started the download process running on the clients. We added more client virtual machines as we debugged the client and gained confidence in it.


Current Issues
==============

We need a better way of controlling the small virtual machines running the image download client script. We are looking at using Salt to do this.

We need to combine the full databases resulting from running the API search scripts with the 100 million image database.

We need to make configuring the clinets more secure.
