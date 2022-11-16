#!/usr/bin/python

from socket import socket, AF_INET, SOCK_STREAM, IPPROTO_TCP, TCP_NODELAY,   SHUT_RDWR
from socket import error as socket_error
import sys
import time
import threading
import cmd
import json
import queue
import struct
import random
import logging
import os
import os.path
import functools
import string

PCMLOG_OFFSET=2

class popoto:
    '''  
    An API for the Popoto Modem product

    This class can run on the local Popoto Modem,  or can be run
    remotely on a PC.

    All commands are sent via function calls, and all JSON encoded responses and status
    from the modem are enqueued as Python objects in the reply queue.

    In order to do this, the class launches a processing thread that looks for replies 
    decodes the JSON and adds the resulting python object into the reply queue. 

    The Popoto class requires an IP address and port number to communicate with the Popoto Modem.
    This Port number corresponds to the base port of the modem application.


    '''

    ROBOT_LIBRARY_SCOPE='GLOBAL'
    def __init__(self, ip='localhost', basePort=17000, logname=None):
        logging.basicConfig() 
        
        self.logger = logging.getLogger(logname)
        self.logger.info("Popoto Init Called")        
        self.pcmplayport = basePort + 5
        self.pcmioport  = basePort+3
        self.pcmlogport = basePort+2
        self.dataport   = basePort+1
        self.cmdport    = basePort
        self.rawTerminal = False
        self.quiet = 0
        self.logger.info("Opening Command Socket")
        self.cmdsocket=socket(AF_INET, SOCK_STREAM)
        self.cmdsocket.connect((ip, basePort))
        self.cmdsocket.settimeout(20)
        self.verbose = 2 
        self.SampFreq = 102400        
        self.pcmplaysocket = 0
        self.recByteCount = 0
        self.ip = ip
        self.is_running = True
        self.fp = None
        self.fileLock = threading.Lock()
        self.logger.info("Starting Command Thread")
        self.rxThread = threading.Thread(target=self.RxCmdLoop, name="CmdRxLoop")
        self.rxThread.start()
        self.replyQ = queue.Queue()
        self.datasocket = None
        self.logger.info("Starting pcmThread")
        self.intParams = {}
        self.floatParams = {}
        self.paramsList = []
        
        self.isRemoteCmd = False
        self.remoteCommandAck = -1
        self.getAllParameters()
        self.remoteCommandHandler = None
        self.CurrentCommandRemote = False
        self.MapPayloadModesToRates=[80,5120,2560,1280,640,10240]

    def setRawTerminal(self):
        self.rawTerminal = True
    def setANSITerminal(self):
        self.rawTerminal = False

    def setRemoteCommandHandler(self, obj):
        self.remoteCommandHandler = obj
        return
    
    def send(self, message):
        """
        The send function is used to send a command  with optional arguments to Popoto as
        a JSON string

        :param      message:  The message contains a Popoto command with optional arguments
        :type       message:  string
        """
        args = message.split(' ', 1)


        # Break up the command and optional arguements around the space
        if len(args) > 1:
            command = args[0]
            arguments = args[1]
        else:
            command = message
            arguments = "Unused Arguments"

        if(self.isRemoteCmd):
        
            if(self.remoteCommandAck):
                command = "RemoteCommandWithAck"
            else:
                command = "RemoteCommand"

            arguments = message 
        

        # Build the JSON message
        message = "{ \"Command\": \"" + command + "\", \"Arguments\": \"" + arguments + "\"}"
        if(self.verbose > 0):
            print(message)
        # Send the message to the command socket
        try:
            if self.verbose > 2:
                self.logger.info("Port:" + str(self.cmdport)+ " >>>> " + message)
            message = message +'\n'
            self.cmdsocket.sendall(message.encode())
        except Exception as e:
            print(e)
            self.logger.error("Port:" + str(self.cmdport)+ " >>>> " + "SEND ERROR")
            
    def sendRemoteStatus(self, message):
        status = "RemoteStatus "+ message
        self.drainReplyQ()

        self.send(status)

        self.waitForSpecificReply("Alert", "TxComplete", 20)

    def setRemoteCommand(self, AckFlag):
        ''' 
            Sets up the python API to send a command to a remote modem over acoustic
            channels.  The RemoteNode variable controls which modem to send the command to

        '''
        self.isRemoteCmd = True
        if(AckFlag):
            self.remoteCommandAck = True
        else:
            self.remoteCommandAck = False
    def setLocalCommand(self):
        ''' 
            Sets up the python API to send a command to the local modem 
        '''
        self.isRemoteCmd = False
        self.remoteCommandAck = False
    def drainReplyQ(self):
        """
        This function reads and dumps any data that currently resides in the
        Popoto reply queue.  This function is useful for putting the replyQ in a known
        empty state.
        """
        while self.replyQ.empty() == False:
            print(self.replyQ.get())

    def drainReplyQquiet(self):
        """
        This function reads and dumps any data that currently resides in the
        Popoto reply queue.  This function is useful for putting the replyQ in a known
        empty state.
        """
        while self.replyQ.empty() == False:
            self.replyQ.get()
    
    def waitForReply(self, Timeout=10):
        """
        waitForReply is a method that blocks on the replyQ until either a reply has been
        received or a timeout (in seconds) occurs.
        
        :param      Timeout:  The timeout 
        :type       Timeout:  { type_description }
        """
        try:
            reply = self.replyQ.get(True, Timeout)
        except: 
            reply = {"Timeout":0}
        return reply
    def waitForSpecificReply(self, Msgtype, value, Timeout=10):
        """
        waitForReply is a method that blocks on the replyQ until either a reply has been
        received or a timeout (in seconds) occurs.
        
        :param      Timeout:  The timeout 
        :type       Timeout:  { type_description }
        """
        done = 0
        start = time.time()
        try:
            while (done == 0 ):
                reply = self.replyQ.get(True, Timeout)
                if(Msgtype in reply ):
                    if(value != None):
                        if(reply[Msgtype] == value):
                            done =1
                        elif type(reply[Msgtype]) == str:
                            if(value in reply[Msgtype]):
                                done = 1 
                    else:
                        done = 1
                elapsedTime = time.time() - start
                if(elapsedTime > Timeout):
                    reply = {"Timeout": 0}
                    return reply
        except: 
            reply = {"Timeout":0}
        return reply
    def startRx(self):
        """
        startRx places Popoto modem in receive mode.
        """
        self.send('Event_StartRx')

    def calibrateTransmit(self):
        """
        calibrateTransmit send performs a calibration cycle on a new transducer
        to allow transmit power to be specified in watts.  It does this by sending
        a known amplitude to the transducer while measuring voltage and current across 
        the transducer.  The resulting measured power is used to adjust scaling parameters
        in Popoto such that future pings can be specified in watts.
        """
        self.setValueF('TxPowerWatts', 1)
        self.send('Event_startTxCal')

    def transmitJSON(self, JSmessage):
        """
        The transmitJSON method sends an arbitrary user JSON message for transmission out the 
        acoustic modem. 
        
        :param      JSmessage:  The Users JSON message
        :type       JSmessage:  string
        """
        
        # Format the user JSON message into a TransmitJSON message for Popoto   
   
        message = "{ \"Command\": \"TransmitJSON\", \"Arguments\": " +JSmessage+" }"
        
        # Verify the JSON message integrity and send along to Popoto
        try:
            testJson = json.loads(message)
            print("Sending " + message)
            message = message + '\n'
            self.cmdsocket.sendall(message.encode())
        except:
            print("Invalid JSON message: ", JSmessage)

    def getVersion(self):
        """
        Retrieve the software version of Popoto
        """
        self.send('getVersion')

    def sendRange(self, power=.1):
        """
        Send a command to Popoto to initiate a ranging cycle to another modem
        
        :param      power:  The power in watts
        :type       power:  number
        """
        self.setValueF('TxPowerWatts', power)
        self.setValueI('CarrierTxMode', 0)
        self.send('Event_sendRanging')
    
    def recordStartTarget(self,filename, duration):
        """
        Initiate recording acoustic signal .rec data to the local SD card.
        Recording is passband if  Popoto 'RecordMode' is 0
        Recording is baseband if  Popoto 'RecordMode' is 1
        
        :param      filename:  The filename on the local filesystem with path
        :type       filename:  string
        :param      duration:  The duration in seconds for continuous record to split-up
                                files with autonaming.  Typical value is 60 for 1 minute files.
        :type       duration:  number
        """

        if filename[:10] != '/captures/' and os.path.exists("/captures"):
            filename = '/captures/' + filename
            print("File recording in /captures/ directory: " + filename)
        self.send('StartRecording {} {}'.format(filename, duration))

    def recordStopTarget(self):
        """
        Turn off recording to local SD card
        """
        self.send('StopRecording')          

    def playStartTarget(self,filename, scale):
        """
        Play a PCM file of 32bit IEEE float values out the transmitter
        Playback is passband if  Popoto 'PlayMode' is 0
        Playback is baseband if  Popoto 'PlayMode' is 1
        
        :param      filename:  The filename of the pcm file on the SD card
        :type       filename:  string
        :param      scale:     The transmitter scale value 0-10; higher numbers result in
                                higher transmit power.
        :type       scale:     number
        """
        if filename[:10] != '/captures/' and os.path.exists("/captures"):
            filename = '/captures/' + filename
            print("File playing from /captures/ directory: " + filename)
        print ("Playing {} at Scale {}".format(filename, scale))    
        self.send('StartPlaying {} {}'.format(filename, scale))
    
    def playStopTarget(self):
        """
        End playout of stored PCM file through Popoto transmitter 
        """
        self.send('StopPlaying')

    def set(self, Element, value):
        """
        Sets a value of a Popotovariable
        
        :param      Element:  The name of the variable to be set
        :type       Element:  string
        :param      value:    The value
        :type       value:    integer or float
        """
        self.send('SetValue {} {} 0'.format(Element, value))
        
    def get(self, Element):
        """
        gets a value of a Popoto  variable
        
        :param      Element:  The name of the variable to be set
        :type       Element:  string
        :param      value:    The value
        :type       value:    integer or float
        """
        self.send('GetValue {}   0'.format(Element))
        
    def setValueI(self, Element, value):
        """
        Sets an integer value of a Popoto integer variable
        
        :param      Element:  The name of the variable to be set
        :type       Element:  string
        :param      value:    The value
        :type       value:    integer
        """
        self.set(Element, value)    

    def setValueF(self, Element, value):
        """
        Sets a 32bit float value of a Popoto float variable
        
        :param      Element:  The name of the variable to be set
        :type       Element:  string
        :param      value:    The value
        :type       value:    float
        """
        self.set(Element, value)     

    def getValueI(self, Element):
        """
        Gets an integer value of a Popoto integer variable
        
        :param      Element:  The name of the variable to be retreived
        :type       Element:  string
        :returns    value:    The value
        :type       value:    integer
        """
        self.get(Element)       

    def getValueF(self, Element):
        """
        Gets the 32bit floating value of a Popoto float variable
        
        :param      Element:  The name of the variable to be retreived
        :type       Element:  string
        :returns    value:    The value
        :type       value:    float
        """
        self.get(Element)       

    
    def tearDownPopoto(self):
        """
        The tearDownPopoto method provides a graceful exit from any python Popoto script

        """
        done=0
        self.getVersion()
        self.is_running = False
        time.sleep(1)

    def setRtc(self, clockstr):
        """
        Sets the real time clock.
        
        :param      clockstr:  The clockstr contains the value of the date in string
                                format YYYY.MM.DD-HH:MM;SS
                                Note: there is no error checking on the string so make it right
        :type       clockstr:  string
        """
        self.send('SetRTC {}'.format(clockstr))

    def getRtc(self):
        """
        Gets the real time clock date and time.
        
        :returns     clockstr:  The clockstr contains the value of the date in string
                                format YYYY.MM.DD-HH:MM;SS
        :type       clockstr:   string
        """
        self.send('GetRTC')

    def __del__(self):
        # Destructor
        done = 0

        # Read all data out of socket
        self.is_running = False


    def playPcmLoop(self, inFile, scale, bb):
        """
        playPcmLoop 
        Play passband/baseband rec file (Note file must be at least 4 seconds long)  
        :param      inFile:  In file
        :type       inFile:  string
        :param      bb:      selects passband (0) or baseband (1) data
        """
        self.pcmplaysocket=socket(AF_INET, SOCK_STREAM)
        self.pcmplaysocket.connect((self.ip, self.pcmplayport))
        self.pcmplaysocket.settimeout(1)
        if(self.pcmplaysocket == None):
            print("Unable to open PCM Log Socket")
            return
        # Set mode to either passband-0 or baseband-1
        self.setValueI('PlayMode', bb)
        
        # Start the play
        self.send('StartNetPlay 0 0')
       
        # Open the file for playing
        fpin  = open(inFile, 'r')
        if(fpin == None):
            print("Unable to Open {} for Reading")
            return
        s_time = time.time()
        sampleCounter = 0 
        if(bb):
            SampPerSec = 10240 *2
        else:
            SampPerSec = 102400
        gain = struct.pack('f', scale)
        if('rec' in inFile[-4:] ):
            print('Playing a rec file')
            readLen = 642*4
            startOffset = 8
        else:
            print('Playing a raw file')
            readLen = 640*4
            startOffset = 0

        Done = 0
        while Done == 0:
            # Read socket of pcm data
            fdata = fpin.read(readLen)
            if(len(fdata) < readLen):
                print('Done Reading File')
                Done = 1
            fdata = gain + gain + fdata[startOffset:]
            StartSample = sampleCounter
            while(sampleCounter == StartSample and len(fdata) > 8):
                try:
                    self.pcmplaysocket.send(fdata) # Send data over socket
                    sampleCounter += (len(fdata)-8)
                  
                except:
                    print('Waiting For Network SampleCount {}'.format(sampleCounter))
                    print(sys.exc_info()[0])
                    Done = 1
        
        duration = sampleCounter / (4*SampPerSec)  #  Bytes to Floats->seconds
        print('Duration {}'.format(duration))

        while(time.time() < s_time+duration):
            time.sleep(1)            
        
        # Terminate play
        self.send('Event_playPcmQueueEmpty')
    
        print("Exiting PCM Loop")
        self.pcmplaysocket.close()
        fpin.close()


    def recPcmLoop(self, outFile, duration, bb):
        """
        recPcmLoop records passband/baseband rec file for duration seconds.  
        This function also returns a vector of timestamps in pcmCount and a vector of 
        HiGain_LowGain flags 0=lo,1=hi which indicate which A/D
        channel was selected on a frame basis
        
        Code sets baseband mode as selected on input, but changes back to pass
        band mode on exit.  Base band recording and normal modem function are
        mutually exclusive, as they share the Modem's Digital up converter.

        :param      outFile:   The output filename with path
        :type       outFile:   string
        :param      duration:  The duration of recording in seconds
        :type       duration:  number
        :param      bb:        passband or baseband selection
        :type       bb:        number 0/1 passband/baseband
        """
        print('Opening ' + outFile)         
        # Open and configure streaming port 
        self.pcmplaysocket=socket(AF_INET, SOCK_STREAM)
        self.pcmplaysocket.connect((self.ip, self.pcmlogport))
        self.pcmplaysocket.settimeout(1)

        # Set mode to either passband-0 or baseband-1
        self.setValueI('RecordMode', bb)
        if(bb == 1):
            duration = duration * 10240 * 2   # Baseband rate 10240 Cplx samples /sec
        else:
            duration = duration * 102400

    
        if(self.pcmplaysocket == None):
            print("Unable to open PCM Log Socket")
            self.setValueI('RecordMode', 0)
            return

        # Open the recording file
        fpout = open(outFile,'w')
        if(fpout == None):
            print("Unable to Open {} for Writing")
            self.setValueI('RecordMode', 0)
            return      
              
        self.recByteCount = 0
        Done = 0
        while Done == 0:
            # Read socket
            try:
                fromRx=self.pcmplaysocket.recv(642*4) # Read the socket
                if fpout != None:
                    fpout.write(fromRx)     # write the data
                self.recByteCount = self.recByteCount + len(fromRx)-2
                if (self.recByteCount >= duration*4):
                    Done=1
                FrameCounter = FrameCounter + 1
                if FrameCounter > 80:
                    print('.')
                    FrameCounter = 0
            except:
                continue



        print("Exiting PCM Loop")
        self.pcmplaysocket.close()
        fpout.close()
        self.setValueI('RecordMode', 0)

    def statReport(self, line):
        if(self.CurrentCommandRemote):
            self.sendRemoteStatus(line)
            print(line)
        else:
            print(line)
      
    def streamUpload(self, filename, power, PayloadMode =1):
        """
        streamUpload Upload a file for acoustic transmission
        
        :param      filename:  The filename to be sent with path
        :type       filename:  string
        :param      power:     The desired power in watts
        :type       power:     number
        """
        if(self.isRemoteCmd):
            self.send('upload ' + filename + ' ' + str(power))
            return


        if(self.datasocket == None):            
            self.datasocket=socket(AF_INET, SOCK_STREAM)

            self.datasocket.connect((self.ip, self.dataport))
            self.datasocket.settimeout(10)
            self.datasocket.setsockopt(IPPROTO_TCP, TCP_NODELAY, 1)

            if(self.datasocket == None):
                self.statReport("Unable to open data Socket")
                return
           
        if os.path.isfile(filename) and os.access(filename, os.R_OK):
            print("File exists and is readable")
            nbytes = os.path.getsize(filename)
            if(nbytes == 0):
                self.statReport("ZERO LENGTH FILE NOT UPLOADING")
                return
            print("File is %d bytes" % nbytes )  
        else:
            self.statReport ("Either the file is missing or not readable")
            return
        print("OK")
        self.statReport ("OK")
        # All good with the file lets upload
        done = 0
        while(done == 0):
            try:
                self.replyQ.get(False)
            except:
                done =1
        sFrame = min(2048, nbytes) # Maximum super frame size
        bytesUploaded = 0
        self.setValueI('TCPecho',0)
        self.setValueI('ConsolePacketBytes', 256)
        self.setValueI('ConsoleTimeoutMS', 100)
        self.setValueI('StreamingTxLen', sFrame)
        self.setValueI('PayloadMode', PayloadMode)
        self.setValueF('TxPowerWatts', power)
   
        done = 0
        while(done == 0):
            time.sleep(.1)
            resp = self.replyQ.get()
            print("Got a response")
            print(resp)
            if('PayloadMode' in resp['Info']):
                done = 1
            Msg = {}
            Msg['Payload'] = {}

# Read each character and send it to the socket
        sent=0
        self.drainReplyQquiet()
        
        with open(filename,'rb') as f:
            PacketsTransmitted = 0
            while(bytesUploaded < nbytes):
                sFrameSent = 0
                print ("Bytes Uploaded {}  nbytes {}".format(bytesUploaded, nbytes))
                while(sFrameSent < sFrame):
                    print ("SFrameSent {}  sFrame {}".format(sFrameSent, sFrame))
                    readLen = sFrame-sFrameSent
                    if(readLen > 256):
                        readLen = 256
                    fileChars = f.read(readLen)

                    Msg['Payload']["Data"] = list(fileChars)
                    '''
                    for i in range(0, len(Msg['Payload']['Data'])):
                        Msg['Payload']['Data'][i] = ord(Msg['Payload']['Data'][i])
                    '''
                    jmsg = json.dumps(Msg)
                    #print(jmsg)
                    try:
                        self.transmitJSON(jmsg)
                        #count=self.datasocket.send(fileChars)
                    except:
                        print("ERROR SENDING ON  DATA SOCKET")
                    bytesUploaded += len(fileChars)
                    print('Bytes Uploaded ' + str(bytesUploaded))
                    sFrameSent += len(fileChars)
                    # WAIT FOR COMPLETE
                PacketsTransmitted += 1
                
                if((nbytes - bytesUploaded) < sFrame):
                    sFrame = nbytes-bytesUploaded
        # Compute the number of seconds to wait for a Complete message
        # Based on the payload mode.  Up it by factor of 10 to account
        # for headers etc, and the "timeout" nature of a timeout.  
        # in the normal case we won't wait this long, as the complete message
        # will arrive. 
        timeout = 10*(nbytes * 8) / self.payLoadModeToBitRate(PayloadMode) 
        timeout
        repl = self.waitForSpecificReply("Alert",'TxComplete', timeout)
            

        print("Upload Complete")
        self.setValueI('PayloadMode', 0)
        self.setValueI('StreamingTxLen', 0)
      
        f.close()

    def streamDownload(self, filename, remotePowerLevel):
        """
        streamDownload Upload a file for acoustic transmission
        
        :param      filename:  The filename to be recieved with path.   The local file downloaded
                                will have the .download extension appended.

        :param      remotePowerLevel: if the remote power level is specified,
                                        then a remote upload command is issued to the
                                        remote device. 
        
        :type       filename:  string
        """
        #clear reception queue
        TimeoutSec = 60
        self.drainReplyQquiet()
        if(remotePowerLevel):
            self.setValueF('TxPowerWatts', remotePowerLevel)
            
            # Set Remote Mode
            self.setRemoteCommand(0)
            # Issue Remote Command
          
            self.setValueF('TxPowerWatts', remotePowerLevel)
            repl = self.waitForSpecificReply("Alert","TxComplete", TimeoutSec)
          
            self.streamUpload(filename, remotePowerLevel)
            # wait for response ? 
            
            repl = self.waitForSpecificReply("RemoteStatus",None, TimeoutSec)
            self.setLocalCommand()
    
            if(repl['RemoteStatus'] != "OK"):
                print('Remote ERROR:')
                print (repl)
                return
            # Set Local
        



        
        #check for proper response
        f = open(filename+'.download', 'wb')
        filedone =0
        TimeoutSec = 30
        while(filedone == 0):
            repl = self.waitForSpecificReply("Header",None, TimeoutSec)
            if('Timeout' in repl):
                print ("Download Complete")
                filedone = 1
                SuperFrameDone = 1
            else:
                SuperFrameDone = 0
                TimeoutSec = 10

            while(SuperFrameDone == 0):
                reply = self.replyQ.get()    
                if "Data" in reply:
                    byte_arr = reply['Data']
                    #file data in to buffer byte array
                    f.write(bytearray(byte_arr))
                elif "Alert" in reply:
                # check for CRC Error  Increment count
                    if reply['Alert'] == "CRCError":

                        byte_arr = [176] * 256
                        f.write(bytearray(byte_arr))
                elif "Info" in reply:
                    if "MODEM_Enable" in reply['Info']  :
                        SuperFrameDone = 1
              
            # check for Modem Enable ? is that a Info ?
            # done = 1
            # Timeout Done = 1
        f.close()
                
            
        #write byte array to disk


    def payLoadModeToBitRate(self, payloadMode):
        '''
            Returns the bitrate of the selected payload mode
        '''
        try:
            rate = self.MapPayloadModesToRates[payloadMode]
        except:
            self.logger.error("Invalid payloadMode")
            rate = self.MapPayloadModesToRates[0]
       
        return rate
    
    def BitRateToPayloadMode(self, rate):
        '''
            Returns the bitrate of the selected payload mode
        '''
        try:
            PayloadMode = self.MapPayloadModesToRates.index(rate)
        except:
            self.logger.error("Invalid Rate")
            PayloadMode = 0
       
        return PayloadMode

    def getParametersList(self):
        """
        Gets the parameters list from the system controller.
        """
        return self.paramsList

    def getParameter(self, idx):
        """
        Gets a Popoto control element info string by element index.
        
        :param      idx:  The index is the reference number of the element
        :type       idx:  number
        """
        self.send('GetParameters {}'.format(idx))        


    def getExclusiveAccess(self):
        '''
        Sets a token atomically on the Popoto modem.   If the token is already set, 
        it returns the currently set value. 
        otherwise it sets the value you request, and then returns it to you.
        this can be used to coordinate multiple clients on the popoto command socket
        '''
        self.drainReplyQquiet()
        letters = string.ascii_lowercase
        token = ''.join(random.choice(letters) for i in range(10))
        waitingCounter = 0
        accessGranted = False
        while accessGranted == False:
            self.send('SetMutexToken {}'.format(token) )
            tokenReplyReceived = False
            while(tokenReplyReceived == False):
                if waitingCounter == 5:
                    print ("Forcing Access to Popoto")
                    self.releaseExclusiveAccess()
                    self.send('SetMutexToken {}'.format(token) )
                    waitingCounter = 0
                try:
                    reply = self.replyQ.get(True, 3)    
                    if reply: 
                        if "ExclusivityToken" in reply:
                            if token in reply["ExclusivityToken"]:
                                accessGranted = True
                                tokenReplyReceived = True
                            else: 
                                print("Waiting for ExclusivityToken Process {} has it".format(reply["ExclusivityToken"]))
                                time.sleep(2) 
                                tokenReplyReceived = True
                                waitingCounter += 1  
                except:
                    print ("Waiting for Exclusivity Token")
                    time.sleep(2)
                    waitingCounter += 1
                    self.send('SetMutexToken {}'.format(token) )
          
    def releaseExclusiveAccess(self):
        self.send('SetMutexToken {}'.format('Available'))
        
    
    def getAllParameters(self):
        """
        Gets all Popoto control element info strings for all elements.
        """
        idx = 0

        # if we already have a parameter list file,  load and parse it. 
        if (os.path.exists('ParamsList.txt')):
            with open("ParamsList.txt", 'r') as f:
                self.paramsList = json.load(f)
                self.paramsList.sort(key=lambda x: x.get('Name'))
                for El in self.paramsList:
                    if (El['Format'] == 'int'):
                        self.intParams[El['Name']] = El
                    else:
                        self.floatParams[El['Name']] = El
                return
        verboseCache = self.verbose
        self.verbose = 0
        self.getExclusiveAccess()
        try:
            while idx >= 0:
                self.getParameter(idx)
                reply = self.replyQ.get(True, 3)    
                if reply:    
                    if "Element" in reply:
                        El = reply['Element']
                        if 'nextidx' in El:
                            idx = int(El['nextidx'])
                        if  int(El['nextidx'])  > 0:
                            if (El['Format'] == 'int'):
                                self.intParams[El['Name']] = El
                            else:
                                self.floatParams[El['Name']] = El
                        if El['Channel'] == 0:
                            self.paramsList.append(El)
                        #print('{}:{}:{}'.format(El['Name'], El['Format'], El['description']))
                    else:
                        print(reply)
                else:
                    print("GetParameter Timeout")

                    idx = -1
        except Exception as a:
            print(a)
        with open("ParamsList.txt", 'w') as f:
            json.dump(self.paramsList, f)

        self.verbose=verboseCache
        self.releaseExclusiveAccess()
        
        return
# -------------------------------------------------------------------
# Popoto Internal NON Public API commands are listed below this point
# -------------------------------------------------------------------
    def RxCmdLoop(self):
        errorcount = 0
        rxString = ''
        self.cmdsocket.settimeout(1)
        while(self.is_running == True):
            try:
                data = self.cmdsocket.recv(1)
                if(len(data) >= 1):

                    if ord(data)  != 13:
                        rxString = rxString+str(data,'utf-8')
                     
                    else:
                        
                        idx = rxString.find("{")
                        msgType = rxString[0:idx]
                        msgType = msgType.strip()


                        jsonData = str(rxString[idx:len(rxString)])
                        try:
                            reply = json.loads(jsonData)
                            
                            if self.verbose > 2:
                                self.logger.info("Port:" + str(self.cmdport)+ " <<<< " + str(jsonData))
                            
                            if("RemoteCommand" in reply and self.remoteCommandHandler != None):
                                self.remoteCommandHandler.handleCommand(reply['RemoteCommand'])
                            self.replyQ.put(reply)
                        except Exception as e:
                            print(e)
                            print("Unparseable JSON message " + jsonData)
                            
                        if(self.verbose > 1):
                            if(self.rawTerminal == False):
                                print("\033[1m"+str(jsonData)+"\033[0m")
                            else:
                                print(str(jsonData))
                        if(self.verbose > 0):
                            logging.info(str(jsonData))
                        
                        rxString = ''
            
            except socket_error as s_err:
                #self.logger.error("Port:" + str(self.cmdport)+ " <<<< " + "Receive ERROR")
                errorcount = errorcount +1 
       

    def exit(self):
        print ("Stub for exit routine")
   
    def receive(self):
        data = self.cmdsocket.recv(256)

    def close(self):
        self.cmdsocket.close() 

    def setTimeout(self, timeout):
        self.cmdsocket.settimeout(timeout)

    def getCycleCount(self):
        while self.replyQ.empty() == False:
            self.replyQ.get()

        self.getValueI('APP_CycleCount')
        reply = self.replyQ.get(True, 3)    
        if reply:    
            if "Application.0" in reply:
                self.dispmips(reply)

        else:
            print("Get CycleCount Timeout")


    def dispMips(self, mips):
        v = {}
        print('Name                            |       min  |        max |     total  |      count |    average |  peak mips | avg mips')
        for module in mips:
            v = mips[module]
            name = module 
            print('{:<32}|{:12}|{:12}|{:12.1e}|{:12}|{:12.1f}|{:12.1f}|{:12.1f}'.format(name,v['min'],v['max'],v['total'], v['count'], v['total']/v['count'], v['max']*160/1e6, (160/1e6)*v['total']/v['count'] ))



