Edit the config:
`sudo nano /boot/firmware/config.txt`
Set `camera_auto_detect=0` instead of `1`
Below [all] set:
`dtoverlay=imx708,cam0`

Test:
`rpicam-still --list-cameras`
`rpicam-still -o ~/Klutch/test.jpg`
