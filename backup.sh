#!/bin/bash
# Crontab:
# 15 0 * * * /root/backup.sh


# Make swap file

#if [ ! -f /swapfile ]; then
#    dd if=/dev/zero of=/swapfile count=1024 bs=1M
#    chmod 600 /swapfile
#    mkswap /swapfile
#    echo '/swapfile none swap defaults 0 0' >> /etc/fstab
#    swapon -a
#fi

items=(
"/etc/"
"/var/www"
"/var/lib/mysql"
"/root/mysql.dump"
"/root/package-selections"
"/root/.[^.]*"
"/opt"
"/srv"
)

evsql="mysqldump --all-databases --events --password=root > /root/mysql.dump"

eval $evsql

evdpkg="dpkg --get-selections > /root/package-selections"

eval $evdpkg

ssh -o StrictHostKeyChecking=no 8919@usw-s008.rsync.net mkdir -p /data1/home/8919/${HOSTNAME}

ssh -o StrictHostKeyChecking=no 8919@usw-s008.rsync.net mkdir -p /data1/home/8919/${HOSTNAME}/last-backup-started

count=0
for item in "${items[@]}"
do
  count=$((count+1))
  ssh -o StrictHostKeyChecking=no 8919@usw-s008.rsync.net mkdir -p /data1/home/8919/${HOSTNAME}/$count
  rsync -ar $item 8919@usw-s008.rsync.net:/data1/home/8919/${HOSTNAME}/$count
done

ssh -o StrictHostKeyChecking=no 8919@usw-s008.rsync.net touch /data1/home/8919/${HOSTNAME}/last-backup-finished
