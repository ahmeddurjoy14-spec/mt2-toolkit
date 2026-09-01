#!/system/bin/sh
echo "==FD=="
echo "TERMUX_USB_FD=$TERMUX_USB_FD"
echo "==DEV=="
ls /dev/ 2>&1 | head -20
echo "==TTY=="
ls /dev/tty* 2>&1 | head -10
echo "==USB SYS=="
ls /sys/bus/usb/devices/ 2>&1 | head -10
echo "==PRODUCT=="
cat /sys/bus/usb/devices/1-2/product 2>&1
cat /sys/bus/usb/devices/1-2/idVendor 2>&1
cat /sys/bus/usb/devices/1-2/idProduct 2>&1
