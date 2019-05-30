Webgrow Python Repository

Install a fresh Raspbian Image to SD card.<br/>
Installer for WebGrow Designed for Raspberry Pi

sudo apt-get update<br/>
sudo apt-get upgrade<br/>
sudo apt-get install git<br/>
git clone https://github.com/mobywan1985/WebGrow_INSTALLER.git<br/>
cd WebGrow_INSTALLER<br/>
sudo ./webgrow_installer.sh<br/>
sudo reboot

In a web browser navigate to Pi IP Address.<br/>
Username: admin<br/>
Password: webgrow<br/>

Temperature and humidity are dependent on DHT22 Sensor being connected to the Pi.<br/>
WebCam uses Motion to set up stream and uses default /dev/video device. Only tried USB webcams. Have not tried PiCam <br/>
