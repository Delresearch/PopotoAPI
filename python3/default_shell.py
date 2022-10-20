#!/usr/bin/python

from popoto import popoto
try:
    import cmd as cmd2
    
except:
    import cmd as cmd2
    
import sys
import time
import os
from subprocess import check_output
import subprocess
import logging
import string
import datetime
from select import select
import logging.handlers
import json
import socket
import fcntl
import struct
import threading
import queue
import fnmatch
       
def get_ip_address():
    ips = check_output(['ifconfig', '-a'])
    return(ips)

logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(message)s" )



class default_shell(cmd2.Cmd):
    def __init__(self, initfile="pshell.init"):
        self.popoto = None
        cmd2.Cmd.__init__(self)
        self.debug = True
        self.initfile_name = initfile
        self.prompt = "(DISCONNECTED)Popoto-> "
        self.intro="""

                                       demPo    
                                  ot_ModemP    
                               opoto_Modem      
                             mPopoto_Modem      
                     oto_ModemPopoto_ModemPopot  
                 mPopoto_ModemPopoto_ModemPopoto_ 
              odemPopoto_ModemPopoto_ModemPopoto_Mode         
            _ModemPopoto_ModemPopoto_ModemPopoto_ModemPop     
          to_ModemPopoto_ModemPopoto_ModemPopoto_ModemPopot   
        poto_ModemPopoto_ModemPopoto_ModemPopoto_ModemPopoto_M
       opoto_ModemPopoto_ModemPopoto_ModemPopoto_ModemPopoto_Mo 
      Popoto_ModemPopoto_Modem                     demPopoto_Mode         
      Popoto_ModemPopoto_ModemPopoto_                  opoto_Modem        
       opoto_ModemPopoto_ModemPopot                          ModemP       
       opoto_ModemP                                             emPopoto_M
      Popot                                                      opoto_ModemP
     mPo                                                           opoto_Modem 
                                                                    l        
                                                                     ph
                     Welcome to the Popoto modem Shell!

                          Communicating Naturally
"""
        self.carrier = 30000
        self.done = False
        self.remoteCmdQ = queue.Queue()
       
        self.logger = logging.getLogger(__name__)

        try:
            if os.path.exists("/etc/PopotoSerialNumber.txt"): 
                self.hardwareImplementation = True;
            else:
                self.hardwareImplementation = False
            self.setupGPIOOut(127)
            self.setupGPIOIn(126)
            self.setupGPIOIn(59)
        except:
            print ("Unable to setup GPIOs") 


        
    def emptyline(self):
        return


    def setupGPIOOut(self,pin):
        if self.hardwareImplementation:
            spin = str(pin)
            with  open('/sys/class/gpio/export',"w") as a:
                a.write(str(pin))
            with open('/sys/class/gpio/gpio'+spin+'/direction',"w") as a:
                a.write("out")
            with open('/sys/class/gpio/gpio'+spin+'/value',"w") as a:
                a.write(str(0))
                
       
    def setupGPIOIn(self,pin):
        if self.hardwareImplementation:
            spin = str(pin)
            with open('/sys/class/gpio/export',"w") as a:
                a.write(str(pin))
            with open('/sys/class/gpio/gpio'+spin+'/direction',"w") as a:
                a.write("in")
           


    def precmd(self, line):
        line = processVariableSetGetCmd(line)
        return line

    def processVariableSetGetCmd(self, line):
       
        args = line.split()
        if(len(args) > 0):
            cmd = args[0]
            variableList = []
            try:
               
                if(self.popoto.paramsList != None):
                    for i in self.popoto.paramsList:
                        variableList.append(i["Name"])
                 
                    if(args[0] in variableList):
                        if (len(args) == 2):
                            self.popoto.set(args[0], args[1])
                        else:
                            self.popoto.get(args[0])
                        line=""
            except:
                pass
        return line

    def do_help(self, line):
        '''
            Displays help for commands and variables within the Popoto pshell.
        '''
        args = line.split()

        if(len(args) == 0):
        
            cmd2.Cmd.do_help(self, line)
            print ("System Variables:")
            print ("=================")
            self.print_elements( line)
        else:
            variableList = []
            for i in self.popoto.paramsList:
                variableList.append(i["Name"])

            for a in args:
                if(a in variableList):
                    self.print_elements(a)
                else:
                    cmd2.Cmd.do_help(self, a)

    def do_ls(self, line):
        '''
        Description:
            ls generates a directory listing of the local Popoto storage.
            it takes 2 arguments.  
                1) a directory name 
                2) a regular expression to match for the files to list. 

        Invocation:
            ls <directory name>  <regex>
        Examples:
            ls /captures
            ls . *.rec

        '''
        try:
            if len(line) == 0 :
                line = "."

            args = line.split()

            if len(args) == 1:
                args.append('*')
            listOfFiles = os.listdir(args[0])
            for entry in listOfFiles:
                filestats =os.stat(args[0] + '/' +entry)
                
                if fnmatch.fnmatch(entry, args[1]):
                    print ("{: <30} {: <15} {} ".format(entry, filestats.st_size, time.strftime('%m/%d/%Y %H:%M:%S', time.localtime(filestats.st_mtime)) ))
        except:
            print( ''' Use:  ls  <directory>  [optional file filter]  
                            ls .
                            ls . *.rec
                            ls /captures *.pcm ''')
    def print_elements(self, line):
        args = line.split()
       
        
        count = 0
        for i in self.popoto.paramsList:
            if(len(args) < 1):
                sys.stdout.write("{: <30} ".format(i["Name"] ))
                count = count + 1;
                if(count == 3 ):
                    print(" ")
                    count = 0
            if(i["Name"] in args):
                print("Variable: " + i["Name"])
                print("\t"+i["description"])
                if(i["permissions"] != "R"):
                    print("\tMinimum Value {}      Maximum Value {}".format(i["min_val"], i["max_val"]))
                print("\tPermissions: "+i["permissions"])
        print(" ")

    def do_setEXP0(self,line):
        '''
        Description:
            The EXP0 Pin is a GPIO Output pin available on the Popoto expansion header.  This API
            allows the user to set the value of that pin.  Note that the GPIO pin has limited current drive,
            and if a high current device is to be controlled, it is necessary to use an external FET or 
            relay.   Please see Popoto.com for application notes concerning controlling high current devices. 

        Invocation:
            setEXP0 <1,0>
        Examples:
            setEXP0 0 
                Turn off the EXP0 pin
            setEXP0 1 
                Turn on the EXP0 pin
        '''   
        #if called from within pshell code instead of command line convert number to str
        try:
            line=str(line)
        except:
            pass
 
        newval=line.split(' ')[-1]#split the line in 'setEXP0 high' in to ['setGPIO7_15','high'] and take the last element "high"
 
        if self.hardwareImplementation == True:
            if (newval in [0,'0','false','low','off']):     #checks to see if newval is in the valid list of "off" state indicators
                valfile = open("/sys/class/gpio/gpio127/value", "w")    #opening writing and closing the gpio's value file with the new GPIO value
                valfile.write("0")                                      #opening writing and closing the gpio's value file with the new GPIO value
                valfile.close()                                         #opening writing and closing the gpio's value file with the new GPIO value
                print('set EXP0 to ' +newval +'\r\n')       #prints new state of GPIO
            elif(newval in [1,'1','true','high','on']):     #checks to see if newval is in the valid list of "on" state indicators
                valfile = open("/sys/class/gpio/gpio127/value", "w")    #opening writing and closing the gpio's value file with the new GPIO value
                valfile.write("1")                                      #opening writing and closing the gpio's value file with the new GPIO value
                valfile.close()     
                print('set EXP0 to ' +newval +'\r\n')       #prints new state of GPIO
 
            else:                                     #opening writing and closing the gpio's value file with the new GPIO value
                print("Please set value to one of [0,1,true,false, low, high, on, off]")

        


    def do_getEXP1(self,line):
        '''
        Description:
            The EXP1 Pin is a GPIO Input pin available on the Popoto expansion header.  This API
            allows the user to get the value of that pin.  

        Invocation:
            getEXP1
        Examples:
            getEXP0  
                
        '''   
        #if called from within pshell code instead of command line convert number to str
        value = 0
        if self.hardwareImplementation == True:
            valfile = open("/sys/class/gpio/gpio127/value", "r")    #opening writing and closing the gpio's value file with the new GPIO value
            value = valfile.read(1)                                      #opening writing and closing the gpio's value file with the new GPIO value
            valfile.close()                                         #opening writing and closing the gpio's value file with the new GPIO value
                                                #opening writing and closing the gpio's value file with the new GPIO value
        print("EXP1 set to {} ".format(value) )       #prints new state of GPIO
 

    def do_startrx(self, line):
        '''
         Description:
            This command enables the modem receiver, and returns the modem statemachine to the listening state
            pshell invokes this command automatically at boot up.   
        Invocation:
            startrx
        Examples:
            startrx  
        
        '''
        self.popoto.startRx()


    def handleCommand(self, line):
        self.remoteCmdQ.put(line)


    def RemoteCommandLoop(self):
        while self.done == False: 
            try: 
                RemoteCmd = self.remoteCmdQ.get(True, .1)
                print(RemoteCmd)
                self.popoto.CurrentCommandRemote = True
                self.onecmd(RemoteCmd)
                self.popoto.CurrentCommandRemote = False
            except:
                pass      

    def do_connect(self, line):
        '''
        Description:
            The connect command is used to connect the pshell with the command socket. 
            This is typically the first command executed in the session of a pshell. 
            A successful connection responds with the list of available parameters.
        Invocation:
            connect <ipaddress> <port>
        Examples:
            connect localhost 17000 
            connect 10.0.0.232 17000
        '''
        args = line.split(' ')

        if not (self.popoto == None):
            del(self.popoto)

        self.popoto = popoto.popoto(args[0], int(args[1]))
        print("Connected to " + line)
        self.prompt = "Popoto->"
    
        fh = logging.handlers.RotatingFileHandler('pshell.log.'+args[0]+'.'+args[1], maxBytes=1000000, backupCount=10, encoding=None, delay=False)
        logger = logging.getLogger()
        logger.handlers=[]

        logger.addHandler(fh)

        self.cmdThread = threading.Thread(target=self.RemoteCommandLoop, name="RemotesCmdLoop")
        self.cmdThread.start()
        self.popoto.setRemoteCommandHandler(self)

        self.runInitScript()

    def do_setverbosity(self, line):
        '''
        Description:
            The setverbosity command is used to control the verbosity of the popoto api
            This command takes an integer from 0 to 5. 
            0 = silent
            5 = most verbose
        Invocation:
            setverbosity <value>
        Examples:
            setverbosity 0
            setverbosity 2
        '''
        try:
            self.popoto.verbose=int(line)
        except:
            print("Invalid Command :  Use setverbosity <0-5>")

    def do_getverbosity(self, line):
        '''
        Description:
            The getverbosity command is used to read the current verbosity of the popoto api
            This command returns an integer from 0 to 5. 
            0 = silent
            5 = most verbose
        Invocation:
            getverbosity 
        Examples:
            getverbosity 
        '''
        print(self.popoto.verbose)

    def do_range(self, line):
        '''
        Description:
            Sends a two way range request using approximately <Power> watts.
            This command issues a range request and sends it to the modem at the 
            configured remoteID.  The remote modem holds the request for a predetermined 
            amount of time, and then replys with a range response.   Popoto will then 
            send back a range report consisting of the distance between the modems, and the
            configured speed of sound and the computed round trip time. 
            Note that the Speed of sound, and the ranging hold time are configurable parameters,
            if you do change the ranging hold time, it is imperative that you configure both the 
            local and remote modems to have the same hold time.  Otherwise, Popoto will give erroneous
            range reports. 
        Invocation:
            range <power> 
        Examples:
            range 20

            {"Range":500.002441,"Roundtrip Delay":666.669922,"SpeedOfSound":1500.000000,"Units":"m, ms, meters per second"}
 
        '''
        try:
            self.popoto.sendRange(float(line))
        except:
            print("INVALID COMMAND: Use  range <power value>")

    def do_deepsleep(self, line):
        '''
        Description:
            Place Popoto into Deep Sleep mode to be awakened by a wake up tone on the 
            acoustic interface. Once in deep sleep, any 25Khz acquisiton pattern 
            will wake the popoto modem. This can most easily be generated by sending a ping command
            from the remote modem.   
            Deepsleep is a low power mode that consumes ~150mW.  Awakening from Deepsleep takes approximately
            1 second after the acquisition.           
        Invocation:
            deepsleep
        Examples:
            deepsleep

        
        '''
        self.popoto.send('Event_powerDown 1')
        print ("Entering Deep Sleep Mode")

 

    def do_powerdown(self, line):
        '''
         Description:
            Place Popoto into POWERDOWN mode to be awakened by a wake up tone on the 
            acoustic interface. Once in powerdown mode, any 25Khz acquisiton pattern 
            will wake the popoto modem. This can most easily be generated by sending a ping command
            from the remote modem.      
            Things to note: Powerdown mode is the lowest power state of the Popoto Modem, typically
            ~13mW.  To awaken from Powerdown mode requires ~20 seconds after the acquistion.        
        Invocation:
            deepsleep
        Examples:
            deepsleep

        '''
        self.popoto.send('Event_powerDown 2')
        print ("Entering Deep Sleep Mode")


    def do_mips(self, line):
        '''
        Description:
           Query the popoto modem to determine internal cycle counts for algorithms.
           Cycle counts are returned in a JSON dictionary for parsing by Popoto development tools. 
           This is a typically a command used by the developers. 
        Invocation:
            mips
        Examples:
            mips
        
        '''
        self.popoto.getCycleCount()
    def do_ssb(self, line):
        '''
        Description:
           This command puts the popoto modem in SSB voice mode. In SSB Voice mode, the modem
           is placed in voice reception.  
           In order to transmit,  one of 3 things has to happen:
            1) The Push to talk GPIOs are set to PTT (see user's guide)
            2) The Voice activity detector signals voice present 
            3) The ssbtx command is issued on the pshell prompt. 

           To return to data execute the datamode command. 
        Invocation:
            ssb
        Examples:
            ssb
        
        '''
        self.popoto.send('startVoice')
        self.popoto.setValueI("APP_SystemMode", 2)



    def do_datamode(self, line):
        '''
        Description:
             This command ends voice mode, and returns the device to data mode,
        Invocation:
            datamode
        Examples:
            datamode  
      
        '''
        self.popoto.startRx()
        self.popoto.setValueI("APP_SystemMode", 0)

    def do_getPEP(self, line):
        '''
        Description:
             Returns the peak envelope power of the transmitted waveform. PEP is a metric used to quantify
             the voice transmit power.
        Invocation:
            getPEP
        Examples:
            getPEP
        '''
        self.popoto.getvaluef('PeakEnvelopePower')

    def do_sleep(self, line):
        '''
        Description:
            This command pauses the pshell for N Seconds.   It is useful when writing scripts or commands
            that need to perform tasks at a prescribed interfveal
        Invocation:
            sleep <N> 
                Sleep for N seconds, where N is an integer. 
        Examples:
            sleep 5
        '''
        try:
            time.sleep(int(line))
        except:
            print ('INVALID COMMAND: Use: sleep <N>     \nDelay for N Seconds where N is an integer')

    def do_chat(self,line):
        ''' 
        Description:
             This command puts Popoto into a character chat mode, In chat mode, the user can type
             characters, and they will be transmitted when one of 2 conditions occur. 1)  the user stops typing
             for a period of time greater than ConsoleTimeoutMS,  or 2) a string of characters greater in length 
             than ConsolePacketBytes is  typed.
             ConsoleTimeoutMS and ConsolePacketBytes are Settable Variable parameters.  
        Invocation:
            chat
        Examples:
            chat  
                ctrl-] to exit
        '''
        verbosity = self.popoto.verbose 
        self.popoto.verbose = 0
        subprocess.call(['/usr/bin/telnet localhost {}'.format(self.popoto.cmdport+1)], shell=True)
        self.popoto.verbose = verbosity

    def do_recordstart(self, line):
        '''
        Description:
            starts a recording to the local storage device..

             Filenames are extended with a timestamp. 

            The file(s) will continue to record until the recordstop command is issued

            

        Invocation:
            recordstart <filename> [duration]

            where 
            filename: is the name of the file to record on the target processor
            duration:   Optional parameter that tells how long each individual record file length
            is in seconds.
            
        Examples:
            recordstart /captures/TestCapeCodBay   60

            records a file called TestCapeCodBay<Timestamp>.rec, and rolls the file every 60 seconds, starting
            a new file with the same base filename with a new appended timestamp 
        '''
        args = line.split(" ")
        filename = args[0]
        duration = 0
        if len(args) < 1:
            print ("Use: recordstart <filename> ")
        else:
            if(len(args) > 1):
                if(args[1] == 'local'):
                    self.popoto.recordStart(filename)
                    return
                else:
                    duration = int(args[1])
            print ("Sent record start command to Target")       
            self.popoto.recordStartTarget(filename, duration)
    
    def do_recordstop(self, line):
        ''' 
        Description:
            Stop and close an in-process recording  
        Invocation:
            recordstop
        Examples:
            recordstop  
               
        '''
        args = line.split(" ")

        if(len(args) >= 1):
            if(args[0] == 'local'):
                self.popoto.recordStop() 
                print ("Sent record stop command to Target")
                return

        self.popoto.recordStopTarget()

    def do_disconnect(self,line):
        '''
        Description:
            Disconnect the pshell from the popoto modem application.   This command is sent
            if the user wishes to connect an application via ethernet. 
        Invocation:
            disconnect
        Examples:
            disconnect    
        '''
        self.popoto.tearDownPopoto()
        self.prompt = "(DISCONNECTED) Popoto->"
        self.popoto = None

    def do_playstart(self, line):
        '''
        Description:

            Starts a playback from the local modem's filesystem.
                where filename is the name of the file to play
                where scale factor is a floating point gain to apply to the file

        Invocation:
            playstart <filename> <scale factor>
        Examples:
            playstart /captures/Tone.pcm 1.0
 
        '''

        try:
            
            args = line.split(" ")
            filename = args[0]
            scale = float(args[1])
        except:
            print("Use = playstart <filename> <scale factor>")
            return
        print ("Sent Play start command to Target")     
        self.popoto.playStartTarget(filename, scale)
    
    def do_playstop(self, line):
        ''' 
        Description:
            Stop and close an in-process playback

        Invocation:
            playstop
        Examples:
            playstop
  
               '''
        print("Stopping the Play command")
        self.popoto.playStopTarget()

    def do_setgainmode(self, line):
        '''
         Description:
            Sets the way the modem manages the high and low gain channels
        Invocation:
            setGainMode <0,1,2>

                GainMode 0 = High Gain Only
                GainMode 1 = Low Gain Only
                GainMode 2 = Automatic Gain Selection

        Examples:
            setGainMode 2
            
                
        '''
        self.popoto.setGainMode(int(line))


    def do_setvaluei(self, line):
        '''
        Description: 
            (DEPRECATED) Sets an integer value on the popoto modem
            This API is deprecated in favor of the simpler pshell api which
            allows setting variables without a command.  See examples below.

        Invocation:
           setvaluei  <Element>

        Examples:
            setvaluei UPCONVERT_Carrier 30000

            This expression can be replaced with the simpler

            UPCONVERT_Carrier 30000

        '''
        args = line.split(" ")
        self.popoto.setValueI(args[0], int(args[1]))


    def complete_setvaluei(self, text, line, begidx, endidx):
        if not text:
            completions = [f for f in sorted(self.popoto.intParams)]
        else:
            completions = [f for f in sorted(self.popoto.intParams) if f.startswith(text)]
        return completions  

    def do_setvaluef(self, line):
   
        '''
        Description: 
            (DEPRECATED) Sets an floating point value on the popoto modem
            This API is deprecated in favor of the simpler pshell api which
            allows setting variables without a command.  See examples below.

        Invocation:
           setvaluef  <Element>

        Examples:
            setvaluef TxPowerWatts 10.0

            This expression can be replaced with the simpler

            TxPowerWatts 10.0

        '''

       
        args = line.split(" ")
        self.popoto.setValueF(args[0], float(args[1]))

    def complete_setvaluef(self, text, line, begidx, endidx):

        if not text:
            completions = [f for f in sorted(self.popoto.floatParams)]
        else:
            completions = [f for f in sorted(self.popoto.floatParams) if f.startswith(text)]
        return completions
    def do_getvaluei(self, Element):
        '''
        Description: 
            (DEPRECATED) Returns the value of an integer variable within 
            the Popoto modem. 
            This API is deprecated in favor of the simpler pshell api which
            allows getting variables without a command.  See examples below.

        Invocation:
           getvaluei  <Element>

        Examples:
            getvaluei UPCONVERT_Carrier

            This expression can be replaced with the simpler

            UPCONVERT_Carrier

            Both will return a JSON message like: 
            
            {"UPCONVERT_Carrier":25000}
        '''
        self.popoto.getValueI(Element)
    
    def complete_getvaluei(self, text, line, begidx, endidx):
        if not text:
            completions = [f for f in sorted(self.popoto.intParams)]
        else:
            completions = [f for f in sorted(self.popoto.intParams) if f.startswith(text)]
        return completions


    def do_getvaluef(self, Element):
        '''
        Description: 
            (DEPRECATED) Returns the value of an floating point variable within 
            the Popoto modem. 
            This API is deprecated in favor of the simpler pshell api which
            allows getting variables without a command.  See examples below.

        Invocation:
           getvaluef  <Element>

        Examples:
            getvaluef TxPowerWatts

            This expression can be replaced with the simpler

            TxPowerWatts

            Both will return a JSON message like: 
            
            {"TxPowerWatts":1.000000}
        '''
        self.popoto.getValueF(Element)

    def complete_getvaluef(self, text, line, begidx, endidx):
        if not text:
            completions = [f for f in sorted(self.popoto.floatParams)]
        else:
            completions = [f for f in sorted(self.popoto.floatParams) if f.startswith(text)]
        return completions

    def do_enablemsmlog(self, line):
        '''
        Description: 
            This api enable logging of modem statemachine transitions.   These transition sare
            logged in the popoto.log file on the modem, and are noted with the ENTER STATE
            text 
        Invocation:
          enablemsmlog

        Examples:
            enablemsmlog
            
        '''
        self.popoto.send('EnableMSMLog')

    def do_disablemsmlog(self, line):
        '''
        Description: 
            This api disables logging of modem statemachine transitions.  
        Invocation:
            disablemsmlog

        Examples:
            disablemsmlog
          '''
        self.popoto.send('DisableMSMLog 0  ')

    def do_configure(self, line):
        '''
        Description: 
            This api configures the modem for different modulation schemes.   It is used
            to allow switching between major operating modes such as Janus and default Popoto 
            modes.   Invocation of this command issues a reboot, after which the modem is in the 
            new mode of operation. 
        Invocation:
          configure <MODE>

        Examples:
           
            configure Janus  
                to setup Janus mode

            configure Popoto
                to setup Popoto Mode

        '''
        print("Selecting Configuration: " + line)
        if(os.path.isdir('/home/root/'+line+"Exes")):
            subprocess.check_output(["/bin/systemctl", "stop", "popoto.service"])
            filename = 'platform.out'
            newfile = '/home/root/'+line+"Exes/"+filename
            oldfile = "/lib/firmware/"+filename
            print ("copy "+newfile + " "+oldfile )
            shutil.copy(newfile,oldfile )

            filename = 'popoto_app'
            newfile = '/home/root/'+line+"Exes/"+filename
            oldfile = "/home/root/"+filename
            print ("copy "+newfile + " "+oldfile )
            
            shutil.copy(newfile,oldfile )
            
            print ("Finished reconfiguring the modem... Rebooting Please wait")
            subprocess.check_output("/bin/sync")

            subprocess.check_output("/sbin/reboot")
        else:
            print("Invalid configuration: "+line)

    def complete_configure(self,text, line, begidx, endidx):
        files = os.listdir(".")
        configurations=[]
        for item in files :
            if os.path.isfile(item)== False:
                if(item.endswith("Exes") and item.startswith(text)):
                    configurations.append(item[0:-4])
        return(configurations)
    def do_version(self, line):
        '''
        Description: 
            Return the serial number and software version of the Popoto modem. Each 
            item is returned in an informational JSON message as shown below
        Invocation:
          version

        Examples:
            version 
            
                {"Info ":"Popoto Modem Version 2.7.0 847"}
                {"Info ":"SerialNumber FFFFFFFFFFFFFFFFFFFFF"}
        '''
        if("SET" in line):
            serialNum = eval(input("Input your Serial Number in quotes: "))
            serialNum = serialNum + "     "
            text_file = open("/etc/PopotoSerialNumber.txt", "w")
            text_file.write(serialNum)
            text_file.close()

        self.popoto.getVersion();

    def do_setcarrier25(self, line):
        '''
        Description: 
            A helper function to set the transmit and receive carriers to 25Khz
        Invocation:
            setcarrier25

        Examples:
            setcarrier25
        '''
        self.popoto.setValueI("UPCONVERT_Carrier", 25000)
        self.popoto.setValueI("DOWNCONVERT_Carrier", 25000)
    def do_setcarrier(self, line):
        '''
        Description: 
            A helper function to set the transmit and receive carriers to a value.
            Note that given the version of the modem, there will be different bounds for 
            carrier frequencies. Check documentation UPCONVERT_Carrier and DOWNCONVERT_Carrier
            for details on acceptable ranges. 
        Invocation:
            setcarrier <Carrier Frequency>

        Examples:
            setcarrier 25000
        '''
        args = line.split(" ")
        if len(args) > 0:
            carrier = int(args[0])

            self.popoto.setValueI("UPCONVERT_Carrier", carrier)
            self.popoto.setValueI("DOWNCONVERT_Carrier", carrier)
        else:
            print (" Use:  setcarrier <frequency>")
    def do_setcarrier30(self, line):
        '''
        Description: 
            A helper function to set the transmit and receive carriers to 30Khz
        Invocation:
            setcarrier30

        Examples:
            setcarrier30
        '''
        self.popoto.setValueI("UPCONVERT_Carrier", 30000)
        self.popoto.setValueI("DOWNCONVERT_Carrier", 30000)

    def do_setclock(self, line):
        ''' 
        Description: 
            Set the Realtime clock in the format YYYY.MM.DD-HH:MM;SS
        Invocation:
            setclock <Date Time>

        Examples:
            setclock  2021.04.02-10:22:30
            
        '''
        self.popoto.setRtc(line)
    
    def do_getclock(self, line):
        ''' 
        Description: 
            Get the Realtime clock in the format YYYY.MM.DD-HH:MM;SS
        Invocation:
            getclock 

        Examples:
            getclock 

            2021.04.02-10:22:30
            get the Realtime clock in the format YYYY.MM.DD-HH:MM;SS
        '''
        self.popoto.getRtc()


  
    def do_setTerminalMode(self, line):
        '''
        Description: 
            Set the pshell terminal to raw mode or ANSI mode. 
            ANSI Mode allows for highlighting of responses,
            Raw mode is easier to use if controlling the device programatically
        Invocation:
            setTerminalMode <raw/ansi> 

        Examples:
            setTerminalMode raw
            setTerminalMode ansi
        '''

        if(line == 'raw'):
            print("Setting Raw Mode")
            self.popoto.setRawTerminal()
        elif (line == 'ansi'):
            print ("Setting ANSI mode")
            self.popoto.setANSITerminal()
        
        else:
            print("Unsupported Terminal Mode")


    def do_ping(self, line):
        '''
        Description: 
            Send an acoustic test message.  This api sends the text "Popoto Test Message"
            using the configured data rate, and the approximate specified power level.   It is important to note 
            that calling ping with a power level latches that power level in the transmitter, to be used
            for subsequent transmissions. 
        Invocation:
            ping <Power level> 

        Examples:
            ping 10
            Sends a test message (Popoto Test Message) using approximately 10 watts of power 
        '''
        args = line.split(" ")
        if(len(args) != 1):
            print("Use ping [power level]")
        else:
            try:
                power = float(line)
                self.popoto.setValueF('TxPowerWatts', power)
                
                # We are transmitting a packet, so disable the streaming mode. 
                self.popoto.setValueI('StreamingTxLen', 0)

                self.popoto.transmitJSON("{\"Payload\":{\"Data\":\"Popoto Test Message\"}}")
            except:
                print("Use ping [power level]") 

    def do_multiping(self, line):
        '''
        Description: 
            Send an series of acoustic test messages.  This api sends the text "Popoto Test Message" repeatedly
            using the configured data rate, and the approximate specified power level.  This api is used to 
            run packet level reliability checks.  The power is specified, along with a count, and an interpacket
            delay. 
        Invocation:
            multiping <power Watts> <number of pings>  <delay in seconds>

        Examples:
            multiping 10 20 5

            Will send 20 ping messages at 10 watts with 5 seconds of delay between messages
        '''

        try:
            args = line.split(" ")
            power = float(args[0])
            nping = int(args[1])
            delays = float(args[2])
        
            if(nping > 500):
                nping = 500
            self.popoto.drainReplyQquiet()

            for i in range(1,nping + 1):
                print("********************* Sending Ping {} **********************".format(i))
                self.popoto.setValueF('TxPowerWatts', power)
                # We are transmitting a packet, so disable the streaming mode. 
                self.popoto.setValueI('StreamingTxLen', 0)

                self.popoto.transmitJSON("{\"Payload\":{\"Data\":\"Popoto Test Message\"}}")
                done= False
                while(done == False):
                        try:
                            reply = self.popoto.replyQ.get(True, 1)
                            if("Alert" in reply):
                                if(reply["Alert"] == "TxComplete"):
                                    done = True; 
                                if(reply['Alert'] == "Timeout"):
                                    done = True
                        
                            time.sleep(delays)
                        except:
                            pass
        except:
            
            print('INVALID INPUT: Use multiping <power Watts> <number of pings>  <delay in seconds>')
            
    def do_getIP(self, line):
        '''
        Description: 
            Display the currently configured IP address and status of the Popoto modem 
        Invocation:
            getIP
        Examples:
            getIP
            
            IPv4 Address: eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
            inet 10.0.0.65  netmask 255.255.255.0  broadcast 10.0.0.255
            ether 00:0c:29:36:4f:2f  txqueuelen 1000  (Ethernet)
            RX packets 3178079  bytes 843820500 (843.8 MB)
            RX errors 0  dropped 508  overruns 0  frame 0
            TX packets 2392420  bytes 2432926671 (2.4 GB)
            TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

        '''
        print("IPv4 Address: {} ".format(get_ip_address()))
    

    def do_netrec(self, line):
        '''
        Description: 
            Records a file file using the network sockets
        Invocation:
            netrec <delresearch File> <time in seconds> <BB/PB>
            where 
              delresearch file is a valid filename
              time in seconds is the desired length of the recording
              BB/PB=1 -> Baseband Recording 0->Passband Recording

              Base band carrier is selected by setting the BBAND_PBAND_DownCarrier
              variable. 
        
        Examples:
            netrec TestRecording 20 0

            records the file TestRecording for 20 seconds in Passband

           netrec TestRecording 20 1

            records the file TestRecording for 20 seconds in Baseband
             
        '''
        args = line.split( ' ')
        if(len(args) != 3):
            print("Use netrec <file> <time in seconds> <BB/PB")
            print("where file  BB/PB=1 -> Baseband Recording 0->Passband Recording")
            return
        outFile = args[0]
        try: 
            duration = float(args[1]); 
            bb = int(args[2])
        except:
            print ("Invalid arguments:   type help netrec ")
            return
        self.popoto.recPcmLoop(outFile, duration, bb )

    def do_netplay(self, line):
        '''
        Description: 
            Plays a file file using the network sockets
        Invocation:
            netplay <delresearchfile> <scale> <BB/PB>
            where 
              delresearchfile: is a valid filename
              scale: is a floating point gain to be applied to the signal p
               prior to transmission
              BB/PB:   Baseband or passband  1 -> Baseband Recording 0->Passband Recording

              Base band carrier is selected by setting the BBAND_PBAND_UpCarrier
              variable. 
        
        Examples:
            netplay TestPBRecording 1.0 0

            plays the file TestPBRecording for at a gain of 1.0  in Passband

           netrec TestBBRecording 20 1

            records the file TestBBRecording at a gain of 1.0 in Baseband

      
        '''
        args = line.split( ' ')
        if(len(args) != 3):
            print("Use netplay <file> <scale> <bb/pb>")
            return

        inFile = args[0]
        scale = float(args[1])
        bb = int(args[2])

        self.popoto.playPcmLoop(inFile,scale, bb)

    def  do_q(self, line):
        '''
        Description:
            Minimize (quiet) the output to the console during normal operation.
        Invocation:
            q
        Examples:    
            q
       
        '''
        self.popoto.quiet=1
    def do_unq(self, line):
        '''
        Description:
            Unquiet the output to the console during normal operation.
        Invocation:
            unq
        Examples:    
            unq
        '''
        self.popoto.quiet = 0

    def do_quit(self, line):
        '''
        Description:
            An alias for exit.   Exits Popoto Modem pshell.

            Note:  On hardware pshell,  quit and exit are disabled

        Invocation:
            quit
        Examples:    
            quit
      
      
        '''
        return self.do_exit(line)

    def do_exit(self, line):
        '''
        Description:
            Exits Popoto Modem pshell.

            Note:  On hardware pshell,  quit and exit are disabled

        Invocation:
            exit
        Examples:    
            exit
        '''
        try:
            self.popoto.is_running = False
            self.popoto.tearDownPopoto()
            self.done = True
            time.sleep(3)
        except:
            print("Popoto Modem Not connected")
        self._should_quit = True
        self.stop = True
        return True

    def preparse(self, raw):
        logging.info(self.prompt + " " + raw)
        return raw

    def do_ssb(self, line):
        '''
        Description:
            Place the ssb Voice into Receive mode 
        Invocation:
            ssb
        Examples:    
            ssb
        
        '''
        self.popoto.send('startVoice')
        self.popoto.setValueI("APP_SystemMode", 2)

    def do_ssbtx(self, line):
        '''
        Description:
            Force the SSB Voice mode into Transmit mode
             
        Invocation:
            ssbtx
        Examples:    
            ssbtx

         '''
        self.popoto.send('startVoice')
        self.popoto.setValueI("APP_SystemMode", 3)

    def kbhit(self):
        dr,dw,de = select([sys.stdin], [], [], 0)
        return dr != []

    def do_Rx(self,line):
        '''
        Description:
            Rx  Receive packets and format the output for test purposes.
            Continues to run until a key is hit. 
        
        Invocation:
             Rx  [Verbose Flag]
             Verbose Flag = 1  Output SNR and Doppler info



        Examples:    
            Rx 
                Enter test receive in quiet mode

            Rx 1

                Enter test receive in verbose mode.  
         '''
        try:
            VerbosePrint = int(line)
        except:
            VerbosePrint =0
        self.popoto.verbose=0;
        rxcount=0
        done = False

        print("Beginning  Reception Counter:  Verbose = {} --  Press Any Key to exit Rx Mode".format(VerbosePrint))

        printableset = set(string.printable)
        while(done == False):
            try:
                Reply = self.popoto.replyQ.get(True, 1)
                now = datetime.datetime.now();

                if(VerbosePrint):
                    print("*********** {} ****************".format(Reply))
                if("ClassUserID" in Reply) and ("ApplicationType" in Reply):
                    for id in Reply:
                        print("{}={},".format(id,Reply[id]),end="")
                    if("Cargo" in Reply):
                        print(" ")
                        c = Reply["Cargo"]
                        CargoStr ="".join(map(chr, c))
                        if(Reply['ApplicationType'] == 1):
                            print("Cargo:  {}".format(CargoStr[0:-2]))
                            print("CRC {0:x} {1:x}".format(c[-2], c[-1]))
                        else:
                            print("Cargo:  {}".format(CargoStr))
                        print("Cargo (Hex) ", end="")
                        for d in Reply["Cargo"]:
                            print("{0:x},".format(d), end="")
                        print("")
                    
                else:
                    if("Header" in Reply):
                        rxcount = rxcount + 1
                        print("")
                        print("****************************************** Reception # {} ******************************************".format(rxcount))
                        print("Header :", end ="")
                        for d in Reply["Header"]:
                            print("{0:x},".format(d), end="")
                        print("")
                    elif "Data" in Reply:
                        Data = Reply["Data"]
                        
                        if True: #(set(Data).issubset(printableset)):
                            for d in Data:
                                print("{0:c}".format(d), end="")
                        print("")
                        for d in Reply["Data"]:
                            print("{0:x},".format(d), end="")
                        print("")
                    elif "Alert" in Reply:
                        if(Reply["Alert"] == "CRCError"):
                            rxcount = rxcount + 1
                            print("")
                            print("****************************************** Reception # {} ******************************************".format(rxcount))
                            print("")
                            print ("****************************** CRC ERROR *****************************")
                        
                if "SNRdB" in Reply:
                    print("SNR (dB) = {}".format(Reply["SNRdB"]))
                if "DopplerVelocity" in Reply:
                    print("DopplerVelocity = {} Kts".format(Reply['DopplerVelocity']))
            except:
                if(self.kbhit()):
                    done = True



    def do_upload(self, line):
        """
        Description:
            Uploads a file in streaming mode.  
           
        Invocation:
            upload [filename] [power level]
        Examples:    
            upload myfile 10

        """
        args = line.split(" ")
        if(len(args) != 2):
            print("Use upload [filename] [power level]")
        else:   
            filename = args[0]
            power = float(args[1])
            
            self.popoto.streamUpload(filename, power)


    def do_download(self, line):
        """
        Description:
            downloads a file in streaming mode.  The remote unit must issue an upload.    
            if the start remote start power level is set to other than 0,  the local modem will send an upload command to the 
            remote modem using the specified power level.,  and then begin the download process.   Otherwise it will 
            sit and wait for the remote modem to start on its own. 
    
        Invocation:
            download <filename> [Remote Start Power Level]
           
        Examples:    
            download MyDownload.txt 

            download MyDownload.txt 10
               
       
        """
        args = line.split(" ")

        try:
            sf = int(args[1])
            
        except:
            sf = 0      
        if sf:
            print(" Issuing a remote download of file " + args[0])
        else:
            print("Please start upload on remote unit")
        self.popoto.streamDownload(args[0], sf)

    def do_setRate80(self,line):
        '''
        Description:
            Set the modem payload transmission rate to 80 bits per second
           
        Invocation:
            setRate80
        Examples:    
            setRate80

        '''
        self.popoto.setValueI("PayloadMode", 0)
    def do_setRate10240(self,line):
        '''
        Description:
            Set the modem payload transmission rate to 10240 bits per second
           
        Invocation:
            do_setRate10240
        Examples:    
            do_setRate10240

        NOTE:  This modulation rate is UNCODED, and will only work on very clean channels
                Use with caution. 
        '''
        self.popoto.setValueI("PayloadMode", 5)

    def do_setRate5120(self,line):
        '''
        Description:
            Set the modem payload transmission rate to 5120 bits per second
           
        Invocation:
            setRate5120
        Examples:    
            setRate5120

        '''
        self.popoto.setValueI("PayloadMode", 1)
    def do_setRate2560(self,line):
        ''' 
        Description:
            Set the modem payload transmission rate to 2560 bits per second
           
        Invocation:
            setRate2560
        Examples:    
            setRate2560

        '''
        self.popoto.setValueI("PayloadMode", 2)
    def do_setRate1280(self,line):
        '''
        Description:
            Set the modem payload transmission rate to 1280 bits per second
           
        Invocation:
            setRate1280
        Examples:    
            setRate1280

        Set the local modem to use the 1280 bit per second modulation scheme
        '''
        self.popoto.setValueI("PayloadMode", 3)
    def do_setRate640(self,line):
        '''
        Description:
            Set the modem payload transmission rate to 640 bits per second
           
        Invocation:
            setRate640
        Examples:    
            setRate640

        Set the local modem to use the 640 bit per second modulation scheme
        '''
        self.popoto.setValueI("PayloadMode", 4)

    def do_transmitJSONFiles(self, line):
        '''
        Description:
            Transmit a file of JSON encoded messages to the remote modem.             
           
        Invocation:
            transmitJSONFiles  <filename> <power> <delay between transmissions> <num transmissions per packet>
        
        Examples:    
            transmitJSONFiles JanusTestCase1.txt 10 30 10
            
        '''
        self.popoto.drainReplyQ()

        try:
            args = line.split(" ")
            filename = args[0];
            power = float(args[1])
            delays = float(args[2])
            numTx = int(args[3])
        except:
            print ('Use: testJanus  <filename> <power> <delay between transmissions> <num transmissions per packet> ')
            return

        # We are transmitting a packet, so disable the streaming mode. 
        self.popoto.setValueI('StreamingTxLen', 0)

        self.popoto.setValueF('TxPowerWatts', power)
    
        with open(filename) as fp:
            rline = fp.readline()
            cnt = 1
            txcount = 1 
            totalcount = 1
            while rline:
                if(rline[0] !='#'):
                    print(rline)
                    rline= rline.rstrip()
                    txcount = 1
                    startTime = time.time();
                    for txcount in range(1, numTx+1):
                        now = datetime.datetime.now();

                        print("**********************   Transmission Line {} Iteration {} Total Count {}  Time {}  **********************".format(cnt, txcount, totalcount, now.strftime("%Y:%m:%d %H:%M:%S.%f")))
                        self.popoto.transmitJSON(rline)

                        done = False
                        while(done == False):
                            try:
                                reply = self.popoto.replyQ.get(True, 1)
                                if("Alert" in reply):
                                    if(reply["Alert"] == "TxComplete"):
                                        done = True; 
                                    if(reply['Alert'] == "MAC dumped packet"):
                                        print("******* ALERT ******** MAC layer dumped the packet")
                                        done = True
                            except:
                                if(self.kbhit()):
                                    done = True

                        time.sleep(delays)
                        totalcount += 1
                rline = fp.readline()
                cnt += 1


    def do_transmit(self, line):
        '''
        Description:
            Transmit a string to the remote modem. Strings do not need to be delimited,
            and can have spaces in them.
            This is used for sending data to the remote modem
           
        Invocation:
            transmit <message>
        
            Where message is a text string
        
        Examples:    
            transmit Hello

            transmit Hello World it's me, Popoto
           
            
        '''
        # We are transmitting a packet, so disable the streaming mode. 
        self.popoto.setValueI('StreamingTxLen', 0)

        txMsg = {"Payload":{"Data":line}}
        txStr = json.dumps(txMsg)

        self.popoto.transmitJSON(txStr)

    def do_transmitJSON(self,line):
        '''
        Description:
            Transmit a JSON encoded message to the remote modem.   
            This is used for sending data to the remote modem
           
        Invocation:
            transmitJSON <message>
        
            The structure of the message is 
            {"Payload":{"Data":[<COMMA SEPARATED 8 BIT VALUES>]}}
        
        Examples:    
            transmitJSON {"Payload":{"Data":[1,2,3,4,5]}}
            sends the binary sequence 0x01 0x02 0x03 0x04 0x05
            
            transmitJSON {"Payload":{"Data": "Hello World"}}
           
            sends the text sequence Hello World
        '''
        # We are transmitting a packet, so disable the streaming mode. 
        self.popoto.setValueI('StreamingTxLen', 0)

        self.popoto.transmitJSON(line)
    

    def runInitScript(self):
        try:
            f = open(self.initfile_name, "r")
            print("Initialization file found, running init commands")
            for line in f.readlines():
                try:
                    if not line.strip().startswith("#"):
                        self.onecmd(line)
                except:
                    print("Invalid Command: '"+line+"'")

        except:
            print("No initialization file {} found:  Running with default configuration".format(self.initfile_name))
        
        
       

    def do_remote(self, line):
        '''
        Description:
            Toggles remote mode.   In remote mode, any command issued at the pshell
            is wrapped into an acoustic message and transmitted to the remote modem, where 
            the command is executed, and the status is returned in an acoustic message from the 
            remote modem.   Note:  It is not permissable to issue a remote transmission using remote
            mode. 
           
        Invocation:
            remote <on/off>
        
          
        Examples:    
            remote on
                Enables remote mode

            remote off
                Disables remote mode
        NOTE:  You cannot issue a transmit command remotely
        '''

        if(line == "on"):
            self.prompt = "(REMOTE)Popoto->"

            self.popoto.setRemoteCommand(0)
        elif(line == "off"):
            self.popoto.setLocalCommand()
            self.prompt = "Popoto->"
        else:
            print("Use: remote <on/off>")
        
        
if __name__ == '__main__':

    
    ps = pshell()
    connected = False
    '''
    while connected == False:
        try:
            ps.onecmd('connect localhost 17000')
            connected = True
            ps.prompt = "Popoto-> "
            ps.onecmd('startrx')
        except:
            time.sleep(.1)
    '''
    done =0
    while(done == 0):
        try:

            ps.cmdloop()
            done = 1
        except:
            print("Invalid Input {}".format(sys.exc_info()[0] ))
            ps.intro = ""

