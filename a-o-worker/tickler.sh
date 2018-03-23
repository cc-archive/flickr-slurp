pgrep -f downloader.sh > /dev/null;
if [ $? -eq 1 ]
then
   wget -N -O /root/tickler.sh http://107.170.230.223/tickler.sh
   wget -N -O /root/downloader.sh http://107.170.230.223/downloader.sh
   wget -N -O /root/config.sh http://107.170.230.223/config.sh
   wget -N -O /root/config.sh http://107.170.230.223/ias3upload.pl
   chmod +x /root/downloader.sh
   (/root/downloader.sh >> /root/downloader-cron.log 2>&1) &
fi
