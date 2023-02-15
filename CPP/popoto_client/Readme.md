Popoto C++ API
==============

This directory contains the Popoto API for C++.   The C++ api is a thin layer that adapts C++ library
calls to the native popoto JSON api.  The user creates a popoto_client class and that gives access to 
the command socket, the pcm sockets.   Both command and pcm sockets enqueue their replys in threadsafe queues to allow 
for deferred processing. 

An example application is included which shows command and status interactions as well as play and record features
both over the network streaming interface as well as natively to the popoto hard drive. 

Dependencies
------------

Building the popoto C++ api requires CMAKE version 3.10 or greater and a native or Cross C compiler. 



Directory Structure
-------------------

The directories are layed out as

```

    |-- build
    |-- Example
    |-- include
    |-- popoto_client.xcodeproj
    |   |-- project.xcworkspace
    |   |   |-- xcshareddata
    |   |   `-- xcuserdata
    |   |       `-- jim.xcuserdatad
    |   `-- xcuserdata
    |       `-- jim.xcuserdatad
    |           |-- xcdebugger
    |           `-- xcschemes
    `-- src
```

### build
The build directory contains the outputs of the build process. It has 
*libpopoto_api.a  the static library for use with your application 
*popoto_play_rec_test an executable example that shows how to intract with comand and PCM queues. 
*popoto_play an executable that plays a raw pcm file 


### include
The include files needed for interfacing with the popoto api.    You can reference this directory in your project's build package. 

### src
popoto_api  source files.   

### Example
A test application running under the popoto_api.   This application transmits a signal from one modem to the other,  records the pcm,  and then replays the pcm back to the other modem multiple times.   This test shows use of the commands,  status and Pcm play and record files, as well as network and file based pcm playing and streaming. 


Building
--------
To build for host execution:  
From the main directory,  execute `./build.sh`

This will generate libraries and binaries in the build directory. 

To build for use on the OMAP processor contact Popoto Modem @ info@popotomodem.com  for additional instructions



Running the Example
-------------------

The example software, found in main.cpp. requires 2 modems and 2 transducers.   It is setup for an airtest.   To reconfigure for a tank,  just reduce the transmit power in main.cpp. 

Set the transducers approximately 1/2 meter apart on some foam or other soft material.   Execute the popoto_play_rec_test  executable as described below.   This test will first send a test message from modem 2 to modem 1.

Modem 1 will record the PCM of the test message, and then play it back to modem 2  10 times via Network streaming.   Then the whole process repeats for play and record local files. 

This test requires the modems be configured to transmit to a RemoteID of 255 (or broadcast)


From the build directory, execute

`./popoto_play_rec_test <ip address Modem 1>  <port address Modem1>  <ip address Modem2>  <port address Modem2>  <Playback Gain>  <temporary WAV filename>`

#### ip Address Modem 1 
To obtain the ip Address of your modem, from the `pshell`   execute `getIP`

#### port address Modem 1
If you are running the modem on popoto hardware,  the port address will be 17000   

#### ip Address Modem 2 
To obtain the ip Address of your modem, from the `pshell`   execute `getIP`.   It is important that this IP address be different than Modem1's .   To change the ipAddress,  use `setIP` from the pshell. 

#### port address Modem 2
If you are running the modem on popoto hardware,  the port address will be 17000   

#### Playback gain
This is the gain with which to play  back the recorded modem waveform 

#### temporary PCM filename
This is a filename that will be used to store the Template transmission file as recorded by Modem 1 and then replayed to Modem2. 


Where to look for more info
---------------------------

please visit [Popoto Modem Documentation](www.popotomodem.com/documentation-)

