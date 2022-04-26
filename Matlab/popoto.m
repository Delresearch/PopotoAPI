classdef popoto < handle
    % Interface class for a single popoto modem.  This class connects via
    % TCPIP to the following ports:
    %   Commands are sent/rcvd via cmdport at the baseport
    %   Modem Data for Transmission/Recept is sent/rcvd via dataport at
    %   the baseport+1
    
    %   PCM can be recorded on the pcmlog port at the baseport+2
    %   PCM A/D D/A data is stramed on the pcmio port at the baseport +3
    %   This class contains many methods for communicating with the popoto
    %   modem.
    
    properties
        cmdsocket
        pcmlogsocket
        pcmiosocket
        datasocket
        sport
        dispatcher = cell(9,2)
        validPacketCnt =0;
        pingTimer = 0;
        TxComplete =0;
        carrier = 30000; 
        SampFreq = 102400;
        Framesize   = 5*128;
        cmdport     = 17000;
        dataport
        pcmlogport
        pcmioport
        range = 0;
        ip;
        dspmode=0;
        errorCnt=0;
        validHeaderCnt = 0; 
        constellationPts = [];
        fwd_taps = [];
        bwd_taps =[];
        fwd_taplen = 0;
        bwd_taplen = 0;
        pll_theta_p = [];
        pll_theta_w = [];
        QCounter = 0; 
        mips = [];
        mipslegend = [];
        replyQ={};
        
    end
    
    methods
        function obj= popoto(ip, basePort, streamAudioFlag)
            % Create a popoto instance, referenced by and ip address and a
            % baseport address
            if(nargin() < 2)
                disp('Use popoto <ip> <basePort> [streamAudio=0]');
                disp(' Where streamAudio =1 means send pcm io on baseport+3')
            end
            
            if(nargin() ==2)
                streamAudioFlag = 0;
            end
            
            try
                obj.pcmioport=basePort+3;
                obj.pcmlogport= basePort+2;
                obj.dataport = basePort+1;
                obj.cmdport=basePort;
                obj.cmdsocket=0;
                if(~isempty(ip))
                    obj.ip = ip;
                    obj.cmdsocket = tcpclient(obj.ip, obj.cmdport,'Timeout', 10);
                    obj.datasocket = tcpclient(obj.ip, obj.dataport,'Timeout', 15);
                end
                
                
                if(streamAudioFlag==0)
                    obj.pcmiosocket = tcpclient(obj.ip, obj.pcmioport);
                    
                else
                    obj.dspmode=1;
                end
            catch
                obj = pcmio;
            end
            
        end
        function out = getValueI(obj, Element)
            % This function queries in integer value to a supported popoto
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            cmd=sprintf('GetValue %s int 0', Element);
            ret=obj.sendBlocking(cmd);
            disp(char(ret))
            [type msg]=strtok(char(ret),' ');
            msg=strtok(msg(10:end),'}');
            %disp(msg)
            out = msg;
        end
        function out = getValueF(obj, Element)
            % This function queries a floating point value to a supported popoto
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            cmd=sprintf('GetValue %s float 0', Element);
            ret=obj.sendBlocking(cmd);
            [type msg]=strtok(char(ret),' ');
            msg=strtok(msg(10:end),'}');
            disp(msg)
            out = msg;
        end
        function out = setValueI(obj, Element, val)
            % This function sets an integer value to a supported popoto
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            
            cmd=sprintf('SetValue %s int %d 0', Element, val);
            obj.sendCommandNB(cmd);
            out=cmd;
        end
        function out = setValueF(obj, Element, val)
            % This function sets a float value to a supported popoto
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            
            cmd=sprintf('SetValue %s float %f 0', Element, val);
            ret=obj.sendBlocking(cmd);
            [type msg]=strtok(char(ret),' ');
            msg=strtok(msg(10:end),'}');
            disp(msg)
            out = msg;
        end
        function tp = startRx(obj, enableFlag)
            %This function turns on the popoto receiver
            if(enableFlag)
                
                cmd = sprintf('SetValue MODEM_Enable int 1 0');
                obj.send(cmd);
                tp= "Enable Modem";
            end
            
            cmd = sprintf('Event_StartRx');
            obj.send(cmd);
            tp= "Start Receiver";
        end
        function send(obj, command)
            % This functions sends a command string to the popoto
            % command socket.  It does not wait for any response
            [cmd arg]=strtok(command,' ');
            sendBuf=['{"Command":"' cmd];
            if(length(arg) > 0)
                if(arg(2) == '{')
                    sendBuf=[sendBuf '","Arguments":' arg(2:end) '}' uint8(13)];
                else
            		sendBuf=[sendBuf '","Arguments":"' arg(2:end) '"}' uint8(13)];
                end
            end
            write(obj.cmdsocket, uint8(sendBuf));
            
        end
        function tp = sendRange(obj, power)
            % This function instructs the modem TX to send a ranging
            % message
            if nargin < 2
                power=.1;
            end
            
            obj.setValueF('TxPowerWatts', power)
            cmd = sprintf('Event_sendRanging');
            obj.send(cmd);
            tp= "Sent Ranging";
        end
        function out = getVersion(obj)
            % This function queries Popoto software version
            cmd=sprintf('GetVersion');
            msg=obj.sendBlocking(cmd);
            disp(msg)
            out = msg;
        end
        function out = getRtc(obj)
            % This function queries Popoto real time clock
            % String returns in format YYYY.MM.DD-HH:MM;SS
            cmd=sprintf('GetRTC');
            msg=obj.sendBlocking(cmd);
            disp(msg)
            out = msg;
        end
        function out = setRtc(obj, timestr)
            % This function sets Popoto real time clock
            % Input string is in format YYYY.MM.DD-HH:MM;SS
            % Note: there is no error checking on the string
            cmd=sprintf('SetRTC');
            cmd=[cmd timestr];
            msg=obj.sendBlocking(cmd);
            disp(msg)
            out = msg;
        end
        function [pcm, pcmCount, HiGain_LowGain] = RecPcmLoop(obj, duration, BB)
            % Record passband pcm for duration seconds.  This function also
            % returns a vector of timestamps in pcmCount and a vector of
            % HiGain_LowGain flags 0=lo,1=hi which indicate which A/D
            % channel was selected on a frame basis
            obj.startRx(1);
            if(nargin < 3)
                BB=1;
            end
            obj.SetRecordMode(BB);
            if(obj.pcmlogsocket >0)
                fclose(obj.pcmlogsocket);
                obj.pcmlogsocket = 0;
            end
            disp('Opening PCM Socket')
            obj.pcmlogsocket = tcpclient(obj.ip, obj.pcmlogport,'Timeout', 10);
            disp('PCM Socket Opened')
            obj.pcmlogsocket
            
            duration = duration * obj.SampFreq;
            fr_sz = 640;
            pcm = zeros(duration,1);
            pcmCount = ones(duration, 1);
            HiGain_LowGain = ones(duration, 1);
            
            tic
            
            Bytecount = 1;
            lastCount = 1;
          %  obj.GainAdjustModeL();
             obj.GainAdjustModeH();
            
            while Bytecount < length(pcm)
                % Read socket
                fromRx=read(obj.pcmlogsocket,fr_sz+2, 'int32');
                
                %pull off header
                pcmCount(Bytecount:Bytecount+fr_sz -1) = [fromRx(1):fromRx(1)+fr_sz-1];
                HiGain_LowGain(Bytecount:Bytecount+fr_sz -1) = single(fromRx(2))* HiGain_LowGain(Bytecount:Bytecount+fr_sz -1);
                %Cast and store pcm
                pcm(Bytecount:Bytecount+fr_sz -1) = typecast(int32(fromRx(3:end)),'single');
                Bytecount = Bytecount + fr_sz;
                
                if mod(Bytecount-1, 102400/2) == 0
                    if(lastCount ==1)
                        
                        
                        pwelch(pcm(lastCount:Bytecount-1),2048);
                        axis([0, 1 -130 10]);
                        h = gcf();
                    else
                        
                        pwelch(pcm(lastCount:Bytecount-1),2048);
                        axis([0, 1 -130 10]);
                    end
                    
                    lastCount = Bytecount;
                    
                    drawnow;
                    fprintf('.');
                end
                
            end
            disp('Recording Complete');
            toc
            
            clear ('obj.pcmlogsocket');
            
        end
        function openPCMSocket(obj)
             obj.pcmlogsocket = tcpclient(obj.ip, obj.pcmlogport,'Timeout', 10);
        end
        
        function [pcm,ts, hl] = readPCMSocket(obj, framecount)
            fr_sz = 640;
            
            pcm = zeros(fr_sz * framecount,1); 
            ts = zeros(framecount, 1); 
            hl = ts; 
            j =1; 
            for i = 1:fr_sz:length(pcm)
                fromRx=read(obj.pcmlogsocket,fr_sz+2, 'int32');

                    %pull off header
                ts(j) = single(fromRx(1)); 
                hl(j)  = single(fromRx(2));
                
                %Cast and store pcm
                
                pcm(i:i+fr_sz-1) = typecast(int32(fromRx(3:end)),'single');
                
                j=j+1; 
            end
               
        
        end
        function SetRecordMode(obj, BaseBand)
            %  this function sets the Dolphin modem in BaseBand Recording
            %  Mode
            if(BaseBand)
                BaseBand = 1;
            end
            cmd = sprintf('SetValue RecordMode int %d 0',BaseBand);
            obj.send(cmd);
        end
        function SetPlayMode(obj, BaseBand)
            %  this function sets the Dolphin modem in BaseBand or PassBand
            %  Play Mode.   If BaseBand =1 the file is played as BaseBand
            %  data with the configured Carrier Frequency
            if(BaseBand)
                BaseBand = 1;
            end
            cmd = sprintf('SetValue Play int %d 0',BaseBand);
            obj.send(cmd);
        end
        function tp = recordStartTarget(obj, filename)
            % This function turns on the pcm recorder on the modem hardware
            % and begins saving the pcm to a file named filename.
            cmd = sprintf('StartRecording %s', filename);
            obj.sendBlocking(cmd);
        end
        function tp = recordStopTarget(obj)
            % This function turns off the pcm recorder on the modem hardware
            cmd = sprintf('StopRecording');
            obj.sendBlocking(cmd);
        end
        function out=waitForReply(obj, timeout)
            % Wait for data up to timeout period in the command socket
            % Reply Queue
        
            %save timeout to restore later
            stashTimeout=obj.cmdsocket.Timeout;
            % set new timeout
            if(nargin<2)
                obj.cmdsocket.Timeout=timeout;
            end
        
            out = read(obj.cmdsocket, 1);
            cmd=zeros(1,256);
            count=1;
            while(out ~= 13)
                cmd(count)=out;
                count=count+1;
                out = read(obj.cmdsocket, 1);
            end
            out = char(cmd)
            
            %Restore previous timeout
            obj.cmdsocket.Timeout=stashTimeout;
            
        end
        function drainReplyQ(obj)
            obj.replyQ={};
        end
        function transmitJSON(obj, jmsg)
            %Send an arbitrary JSON message out the Popoto acoustic
            %transmitter
            cmd = '{"Command":"TransmitJSON","Arguments":"}'
            cmd = [cmd jmsg '"}'];
            obj.send(cmd);
        end
        function tearDownPopoto(obj)
            % Tear Down Popoto Object
            clear obj
        end
        function playStartTarget(obj,filename,scale)
            % Play a PCM file of 32bit IEEE float values out the transmitter
            % Playback is passband if  Popoto 'PlayMode' is 0
            % Playback is baseband if  Popoto 'PlayMode' is 1
            
            cmd = 'StartPlaying '
            cmd = [cmd filename ' '  num2str(scale)];
            obj.send(cmd);
        end
        function playStopTarget(obj)
            %End playout of stored PCM file through Popoto transmitter
            obj.send('StopPlaying');
        end
        function tp=calibrateTransmit(obj)
            % calibrateTransmit send performs a calibration cycle on a new transducer
            % to allow transmit power to be specified in watts.  It does this by sending
            % a known amplitude to the transducer while measuring voltage and current across
            % the transducer.  The resulting measured power is used to adjust scaling parameters
            % in Popoto such that future pings can be specified in watts.
            
            obj.setValueF('TxPowerWatts', 1.);
            obj.send('Event_startTxCal');
        end
        function out=getParameter(obj,idx)
            %Gets a Popoto control element info string by element index.
            %:param      idx:  The index is the reference number of the element
            %:type       idx:  number
            cmd='GetParameters ';
            cmd=[cmd num2str(idx)];
            out=obj.sendBlocking(cmd);
            out=deblank(out); %remove trailing spaces
        end
        function getAllParameters(obj)
            % Gets all Popoto control element info strings for all elements.
            idx=0;
            while(idx>=0)
                Elstr=getParameter(obj,idx);
                Element=jsondecode(Elstr);
                Element.Element
                idx=Element.Element.nextidx;
                
            end
            
            
        end
        
        function playPcmLoop(obj,infile,scale, bb)
            % playPcmLoop
            % Play passband/baseband PCM for duration seconds.
            % :param      inFile:  In file
            % :type       inFile:  string
            % :param      bb:      selects passband or baseband data
            % :type       bb:      number 0/1 for pass/base
            disp('Opening PCM Socket')
            obj.pcmlogsocket = tcpclient(obj.ip, obj.pcmlogport,'Timeout', 10);
            disp('PCM Socket Opened')
            obj.pcmlogsocket
            
            % Set mode to either passband-0 or baseband-1
            obj.setValueI('PlayMode', bb)
            
            % Start the play
            obj.send('StartNetPlay 0 0')
            
            % Open the file for playing
            fpin  = fopen(infile, 'rb')
            if(fpin == -1)
                disp("Unable to Open play rec file for Reading")
            else
                s_time = posixtime(datetime(datestr(now)))
                sampleCounter = 0
                if(bb)
                    SampPerSec = (obj.SampFreq/10) *2
                else
                    SampPerSec = obj.SampFreq;
                end
                Done = 0
                Headerlen=2;
                Freclen=obj.Framesize+Headerlen;
                while Done == 0
                    % Read a frame of pcm data from file
                    fdata = int32(fread(fpin,Freclen,'int32'));
                    fdata(1) = typecast(single(scale), 'int32');
                    fdata(2) = fdata(1);
                    if(length(fdata) < Freclen)
                        disp('Done Reading File')
                        Done = 1
                    end
                    StartSample = sampleCounter;
                    while((sampleCounter == StartSample)&& ~isempty(fdata))
                        try
                            write(obj.pcmlogsocket,fdata) % Send data over socket
                            sampleCounter = sampleCounter +(length(fdata)-Headerlen);
                        catch
                            disp('Waiting For Network')
                        end
                    end
                    duration = sampleCounter / (SampPerSec);  %  Bytes to Floats->seconds
                    %                     while(posixtime(datetime(datestr(now))) < s_time+duration)
                    %                         pause(1);
                    %                     end
                end
                % Terminate play
                obj.send('Event_playPcmQueueEmpty')
                
                disp("Exiting PCM Loop")
                ostr=sprintf('Duration %d', duration);
                disp(ostr)
                
                fclose(fpin);
            end
            
        end
        
        function streamUpload(obj,filename, power)
            %streamUpload Upload a file for acoustic transmission
            %
            %:param      filename:  The filename to be sent with path
            %:type       filename:  string
            %:param      power:     The desired power in watts
            %:type       power:     number
            %
            disp('Opening data Socket')
            obj.datasocket = tcpclient(obj.ip, obj.dataport,'Timeout', 10);
            disp('data Socket Opened')
            obj.datasocket
            if isfile(filename)
                % File exists.
                s=dir(filename);
                nbytes=s.bytes;
            else
                % File does not exist.
                disp('File for upload is missing or not readable')
            end
            
            % All good with the file lets upload, first drain all replies
            obj.drainReplyQ();
            
            obj.setValueI('TCPecho',0);
            obj.setValueI('ConsolePacketBytes', 256);
            obj.setValueI('ConsoleTimeoutMS', 500);
            obj.setValueI('StreamingTxLen', nbytes);
            obj.setValueF('TxPowerWatts', power);
            resp=obj.setValueI('PayloadMode', 1);
            
            done = 0;
            while(done == 0)
                pause(.1)
                resp = obj.waitForReply(10);
                disp('Got a response')
                disp(resp)
                if(contains(resp, 'PayloadMode'))
                    done = 1;
                end
            end
            
            
            % Read each character and send it to the socket
            sent=0;
            fid=fopen(filename,'rb');
            
            fileChars = uint8(fread(fid,nbytes,'uint8'));
            write(obj.datasocket,fileChars);
            
            disp('Upload Complete')
            ostr=sprintf('Sent out %d bytes',nbytes);
            disp(ostr)
            fclose(fid);
            
        end
        
        % Matlab only Commands
        function out = sendBlocking(obj, command)
            % This functions sends a command string to the popoto
            % command socket.  It then waits for a response in a
            % blocking mode clear buffer
            send(obj,command);
            sendBuf(1:length(command)) = uint8(command);
            
            out = read(obj.cmdsocket, 1);
            cmd=zeros(1,256);
            count=1;
            while(out ~= 13)
                cmd(count)=out;
                count=count+1;
                out = read(obj.cmdsocket, 1);
            end
            out = char(cmd)
        end
        function [out, ofreq, ologVar, opeak] = dispSpectrum(obj, duration, BB)
            % Record passband pcm for duration seconds.  This function also
            % returns a vector of timestamps in pcmCount and a vector of
            % HiGain_LowGain flags 0=lo,1=hi which indicate which A/D
            % channel was selected on a frame basis
            obj.startRx(1);
            if(nargin < 3)
                BB=1;
            end
            obj.SetRecordMode(BB);
            
            if(obj.pcmlogsocket >0)
                fclose(obj.pcmlogsocket);
                obj.pcmlogsocket = 0;
            end
            disp('Opening PCM Socket')
            obj.pcmlogsocket = tcpclient(obj.ip, obj.pcmlogport,'Timeout', 60);
            disp('PCM Socket Opened')
            obj.pcmlogsocket
            
            duration = duration * obj.SampFreq;
            fr_sz = 640;
            pcm = zeros(1,102400/2);
            out = zeros(1,duration); 
            ofreq = [];
            opeak = [];
            ologVar = [];
            
            tic
            
            Bytecount = 0;
            totalCount  = 0;
            pmatlen = 3; 
            pmat = zeros(pmatlen, 1025);
            outcnt = 0; 
            while totalCount < duration
                % Read socket
                fromRx=read(obj.pcmlogsocket,fr_sz+2, 'int32');
                
                %pull off header
                %Cast and store pcm
                %                 size(pcm(1:Bytecount+fr_sz -1))
                %                 size(typecast(int32(fromRx(3:end)),'single'))
                %
                pcm(Bytecount+1:Bytecount+fr_sz ) = typecast(int32(fromRx(3:end)),'single');
                Bytecount = Bytecount + fr_sz;
                
                if Bytecount >= 102400/2
                    
                    
                    figure(1);
                    plot(pcm);
                    drawnow();
                    figure(2);
                    out(outcnt+1:outcnt+Bytecount)= pcm(1:Bytecount);
                    outcnt = outcnt+Bytecount;
                    pxx = 10*log10(pwelch(pcm(1000:end) ,2048));
                    pxx(1:10) = -110; % Poor mans bias removal
                    pmat(1:pmatlen-1,:) = pmat(2:pmatlen,:);
                    pmat(pmatlen,:) = pxx';
                    
                    plot(linspace(0,51200, length(pxx)),pmat);
                    
                    axis([0, 51200 -120 20]);
                    
                    
                    [peak freq] = max(pxx);
                    freq = freq * 51200/length(pxx);
                    totalCount =totalCount+ Bytecount;
                    Bytecount =1;
                    
                    t=text(3000, -110,['Peak ' num2str(peak) ' Freq ' num2str(freq)]);
                    set(t, 'FontSize', 20)
                    logVar = 10*log10(var(pcm));
                    t=text(3000, -120,['Avg ' num2str(logVar)]);
                    set(t, 'FontSize', 20)
                    drawnow;
                    
                    fprintf('Peak Value %f Avg %f Frequency %f\n', peak, logVar, freq);
                    opeak = [opeak peak];
                    ofreq = [ofreq freq];
                    ologVar = [ologVar logVar];
                    
                end
                
            end
            disp('Recording Complete');
            toc
            
            clear ('obj.pcmlogsocket');
            
        end
        
        % Deprecated Functions ---------------------
        function pcm = service_pass_band(obj, input)
            % This function feeds a vector of input passband data, a single
            % frame at a time to the modem.  Additionally it services both the
            % command socket and data sockets.
            if(obj.dspmode==0)
                pcm = zeros(size(input));
                
                input = int32(typecast(single(input), 'int32'));
                Bytecount = 1;
                loopCount = 0;
                while Bytecount <= length(pcm)-(640-1)
                    
                    % Note: ieee754-32 float flowing through the sockets in 32 bit ints
                    write(obj.pcmiosocket, input(Bytecount:Bytecount+640-1));
                    
                    fromTx=read(obj.pcmiosocket,640, 'int32');
                    pcm(Bytecount:Bytecount+640 -1) = typecast(int32(fromTx),'single');
                    
                    Bytecount = Bytecount +640;
                    
                    obj.serviceCommandSocket();
                    obj.serviceDataSocket();
                    loopCount = loopCount +1;
                    if(loopCount == 100)
                        Bytecount
                        %loopCount = 0;
                    end
                end
            else
                pause(.002)
            end
            
            
        end
        
        function serviceCommandSocket(obj, processFxn)
            % This command services the command socket to see if any data has
            % arrived.  Additionally it sends a keepalive ping every minute
            obj.pingTimer = obj.pingTimer+1;
            if(obj.pingTimer == 160*60)
                sendPing(obj);
                %disp("SendPing");
                obj.pingTimer = 0;
            end
            while(obj.cmdsocket.BytesAvailable > 0)
                %disp("Got A Packet")
                out = read(obj.cmdsocket, 1);
                cmd=zeros(1,2048);
                count=1;
                while(out ~=13)
                    cmd(count)=out;
                    
                    count=count+1;
                    out = read(obj.cmdsocket, 1);
                end
                cmd=cmd(1:count);
                if nargin < 2
                obj.process_response(char(cmd));
                else
                    processFxn(char(cmd))
            end
                obj.replyQ=[obj.replyQ char(cmd)];
        end
        end
   
        function [reply, index] =checkReplyQ(obj, arg)
        obj.serviceCommandSocket();
        index=0;
        location= 0; 
        reply = '';
        for i =1:length(obj.replyQ)
            for j=1:length(arg)
                
                if(contains(obj.replyQ{i},arg{j}))
                    index=j;
                    location = i; 
                    reply = obj.replyQ{i};
                break;
            end
        end
        end
        if(location<length(obj.replyQ))
            trq={};
            j=1;
            for k=location+1:length(obj.replyQ)
                trq{j}=obj.replyQ{k};
                j=j+1;
            end
            obj.replyQ=trq;
        else
            obj.replyQ={};
        end
        end
        function serviceDataSocket(obj)
            %This command checks the data socket for incoming data.  If
            %available it displays in blue color.
            
            if(obj.datasocket.BytesAvailable > 0)
                out = read(obj.datasocket, obj.datasocket.BytesAvailable);
                cprintf('blue', char(out))
                cprintf('black','\n')
            end
        end
        
        function resetTestCounts(obj)
            obj.validPacketCnt=0;
            obj.validHeaderCnt = 0; 
            obj.errorCnt =0;
            obj.TxComplete=0;
        end
        function out=toneMeasure(obj,fc, amp)
            %This debug function switches a mode in the popoto so that it
            % send a carrier instead of a modulated packet when
            % sendTestPacket method is invoked.  The carrier frequency fc
            % is specified and the amplitude (0-.5)
            cmd = sprintf('SetValue UPCONVERT_OutputScale float %f 0',amp);
            disp(cmd)
            obj.sendBlocking(cmd);
            
            obj.SetCarrier(fc);
            
            cmd = sprintf('SetValue CarrierTxMode int 1 0');
            obj.sendBlocking(cmd);
            %     obj.sendBlocking('enableTPA');
            
            obj.sendTestPattern();
            
            [out a b]=obj.recpcm(30);
            
        end
        
        
        function clearCycleCounts(obj)
              obj.mips = [];
              obj.mipslegend = [];
        end
        
         
        function tp=process_response(obj, line)
            % This function processes command responses.  It looks for
            % interesting reports and prints them out accordingly
            
            if(contains(line, 'Constellation'))
                if( ~contains(line, 'PSK_'))
                    startStr = strfind(line, '{');
                    endStr = strfind(line, '}');
                    line = line(startStr:endStr);

                    msg =jsondecode(line);
                    cp = msg.Constellation;
                    
                    cp = complex(cp(1:2:end), cp(2:2:end)); 
    
                    obj.constellationPts = [obj.constellationPts cp.'];
                end
            
            end
            
            if(contains(line, 'Fwd'))
                startStr = strfind(line, '{');
                endStr = strfind(line, '}');
                line = line(startStr:endStr);

                msg =jsondecode(line);
                taps = msg.Fwd;
                
                taps = complex(taps(1:2:end), taps(2:2:end)); 
              
                obj.fwd_taps = [obj.fwd_taps taps];
            
            end
            
            if(contains(line, 'Bwd'))
                startStr = strfind(line, '{');
                endStr = strfind(line, '}');
                line = line(startStr:endStr);

                msg =jsondecode(line);
                taps = msg.Bwd;
                taps = complex(taps(1:2:end), taps(2:2:end));
              
                obj.bwd_taps = [obj.bwd_taps taps];
            
            end
            if(contains(line, 'Pll_theta_p'))
               startStr = strfind(line, '{');
                endStr = strfind(line, '}');
                line = line(startStr:endStr);
                msg =jsondecode(line);
              
                obj.pll_theta_p = [obj.pll_theta_p msg.Pll_theta_p.'];
            
            end
             if(contains(line, 'Pll_theta_w'))
                  startStr = strfind(line, '{');
                endStr = strfind(line, '}');
                line = line(startStr:endStr);
                msg =jsondecode(line);
              
                obj.pll_theta_w = [obj.pll_theta_w msg.Pll_theta_w.'];
            
            end
            
            if(contains(line,'Header'))
                obj.validHeaderCnt = obj.validHeaderCnt+1;
                cprintf('black',line)
                fprintf('\n');
            end
            if(contains(line,'RangeReport'))
                cprintf('red',line)
                fprintf('\n');
                report = jsondecode(line(13:end-1));
                if(exist('report'))
                    obj.range = report.Range;
                end
            end
            if contains(line, 'CRCCheck')
                obj.validPacketCnt = obj.validPacketCnt+1;
%                 str=sprintf('CRC Pass %d',obj.validPacketCnt);
%                 disp(str);
            end
        
            if contains(line, 'TxComplete')
                obj.TxComplete = obj.TxComplete+1;
            end
            
            if contains(line, 'CRCError')
                obj.errorCnt = obj.errorCnt+1;
            end
            
            if contains(line, 'Application.0')
                
     
                startStr = strfind(line, '{');
               
                line = line(startStr:end-1);

                msg =jsondecode(line);

                
                obj.mips = [obj.mips; struct2array(msg)];
                if(length(obj.mipslegend) == 0)
                    obj.mipslegend = fieldnames(msg);
           
                end
            end
            
            
            tp=1;
        end
        function tp=setRate(obj, rate)
            cmd = sprintf('SetValue PayloadMode int %d 0', rate);
            obj.send(cmd);
            tp= "Set Rate";
        end
        
        function tp=setTestMessageLen(obj, bytecount)
            obj.setValueI('PayloadLenBytes', bytecount);
        end
        
     
        
        function resetInstrumentation(obj)
            obj.constellationPts = [];
            obj.fwd_taps = [];
            obj.bwd_taps =[];
            obj.fwd_taplen = 0;
            obj.bwd_taplen = 0;
            obj.pll_theta_p = [];
            obj.pll_theta_w = [];        
        end
        
        function queryInstrumentation(obj)
            if(mod(obj.QCounter, 2)==0) 
                obj.getValueF('PSK_Constellation');
            else
              if(mod(obj.QCounter, 3) == 0)  
                    obj.getValueF('PSK_Taps');
              else
                    obj.getValueF('PSK_PLL');
              end
            end
            obj.QCounter = obj.QCounter +1; 
        end
        
        
        function tp = sendTestPattern(obj)
            % This function instructs the modem TX to send a test packet
            
            cmd = sprintf('SetValue MODEM_Enable int 1 0');
            obj.send(cmd);
            tp= "Enable Modem";
            
            
            cmd = sprintf('Event_sendTestPacket');
            obj.send(cmd);
            tp= "Sent Test Packet";
        end
        
        
        function tp = setDSPmode(obj, dsp)
            % This function confingures the matlab simulation to use the
            % actual a/d d/a pcm data instead of the streaming
            
            obj.dspmode=dsp;
            tp= "Sent DSP Mode";
        end
        
        
        
        function tp = GainAdjustModeL(obj)
            % This function sets the popoto to only use the low gain
            % channel.
            cmd = sprintf('SetValue GainAdjustMode int 0 0');
            obj.send(cmd);
            
        end
        
        function tp = GainAdjustModeH(obj)
            % This function sets the popoto to only use the high gain
            % channel.
            cmd = sprintf('SetValue GainAdjustMode int 1 0');
            obj.send(cmd);
            
        end
        
        function tp = GainAdjustModeAuto(obj)
            % This function sets the popoto to only use the best gain
            % channel for the frame automatically.
            cmd = sprintf('SetValue GainAdjustMode int 2 0');
            obj.send(cmd);
            
        end
        
      
            
        function tp = SetCarrier(obj, i)
            % This function sets the popoto carrier frequency in Hz.
            
            cmd = sprintf('SetValue UPCONVERT_Carrier int %d 0',i);
            obj.send(cmd);
            
            cmd = sprintf('SetValue DOWNCONVERT_Carrier int %d 0',i);
            obj.send(cmd);
        end
        
        function tp = SetMinDev(obj, v)
            % This function sets the minimum detection noise deviation
            
            cmd = sprintf('SetValue FHDEMOD_MinNoiseDeviation float %f 0',v);
            obj.send(cmd);
            
        end
        
        
        function tp = modemDisable(obj)
            % This function disables the modem processing on the popoto
            % hardware.
            cmd = sprintf('SetValue MODEM_Enable int 0 0');
            obj.send(cmd);
            tp= "Disable Modem";
            
        end
        function tp = enableMSMLog(obj)
            % This function enables detailed modem state machine loggin in the popoto.log
            cmd = sprintf('EnableMSMLog');
            obj.send(cmd);
        end
        function tp = disableMSMLog(obj)
            % This function disables detailed modem state machine loggin in the popoto.log
            
            cmd = sprintf('DisableMSMLog');
            tp= obj.sendBlocking(cmd);
        end
        
        function sendPing(obj)
            % This function sends a tcp ping to the MODEM
            obj.send('ping');
        end
        
        function out=sendDPing(obj)
            % This function sends a tcp ping to the MODEM which flows
            % through popoto all the way to DSP and back with a response.
            out=obj.sendBlocking('dping');
        end
        
        function sendDPingNB(obj)
            % This function sends a tcp ping to the MODEM which flows
            % through popoto all the way to DSP and back.  It does not
            % wait for any response.
            obj.send('dping');
        end
        
        function getNoiseStats(obj)
            %This function gets the current noise mean and deviation from
            % the frequency hopping matched filter output
            obj.getValueF('FHDEMOD_NoiseMean');
            obj.getValueF('FHDEMOD_NoiseDev');
        end
        
        function getDetectThresholds(obj)
            %This function gets the detection threshold from
            % the frequency hopping receiver
            obj.getValueF('FHDEMOD_DetectThresholdDB');
            disp(' ');
            disp('-----Bench Mode Numbers------');
            obj.getValueF('FHDEMOD_MinNoiseDetectLevel');
            obj.getValueF('FHDEMOD_BenchPeakLevel');
            
        end
        
        
        function [cycles, legend]= getCycleCounts(obj)
            % This function queries the DSP to get the current cycle count
            % data base.   The return value is parsed in process_response
            %
            cmd='GetValue APP_CycleCount int 0';
            obj.send(cmd);
            cycles = obj.mips;
            legend = obj.mipslegend;
        end   
        
        function out = GetValueI(obj, Element)
            % This function queries in integer value to a supported dolphin
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            cmd=sprintf('GetValue %s int 0', Element);
            ret=obj.sendCommand(cmd);
            disp(char(ret))
            [type msg]=strtok(char(ret),' ');
            msg=strtok(msg(10:end),'}');
            %disp(msg)
            out = msg;
        end
        function out = GetValueF(obj, Element)
            % This function queries a floating point value to a supported dolphin
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            cmd=sprintf('GetValue %s float 0', Element);
            ret=obj.sendCommand(cmd);
            retcell=strsplit(char(ret),char(0));
            outStruct = jsondecode(retcell{1})
            out = getfield(outStruct, Element);
        end
        
        function out = SetValueI(obj, Element, val)
            % This function sets an integer value to a supported dolphin
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            
            cmd=sprintf('SetValue %s int %d 0', Element, val);
            ret=obj.sendCommandNB(cmd);
        end
        function out = SetValueF(obj, Element, val)
            % This function sets a float value to a supported dolphin
            % Element in the modem.  It is used for various configurable
            % parameters in the modem.
            
            cmd=sprintf('SetValue %s float %f 0', Element, val);
            ret=obj.sendCommand(cmd);
            [type msg]=strtok(char(ret),' ');
            msg=strtok(msg(10:end),'}');
            disp(msg)
            out = msg;
        end
        
        function out = sendCommand(obj, command)
            % This functions sends a command string to the dolphin
            % command socket.  It then waits for a response in a
            % blocking mode
            % clear buffer
            sendCommandNB(obj,command);
%             sendBuf(1:length(command)) = uint8(command);
%             
%             out = read(obj.cmdsocket, 1);
%             cmd=zeros(1,256);
%             count=1;
%             while(out ~= 13)
%                 cmd(count)=out;
%                 count=count+1;
%                 out = read(obj.cmdsocket, 1);
%             end
%             out = char(cmd)
        end
        function sendCommandNB(obj, command)
            % This functions sends a command string to the dolphin
            % command socket.  It does not wait for any response
            [cmd arg]=strtok(command,' ');
            sendBuf=['{"Command":"' cmd];
            sendBuf=[sendBuf '","Arguments":"' arg(2:end) '"}' uint8(13)];
            write(obj.cmdsocket, uint8(sendBuf));
            
        end
        
        function outpcm = capture(obj, filename, numSeconds, BBMode)
            % Function to capture data from the dolphin app
            %
            %   filename -->  Matfile  for  storing PCM data
            %
            %   numSeconds -->  Duration of capture
            
            
            if nargin < 2
                fprintf('function out = capture(filename, numSeconds)')
                return;
            end
            
            obj.GainAdjustModeH()
            
            [outpcm,counter, HGLG] = obj.recpcm(numSeconds);
            notes = input('Enter Notes for this capture');
            
            cap.outpcm = outpcm;
            cap.notes = notes;
            cap.counter = counter;
            cap.time = datestr(now);
            
            save(filename, 'cap');
            
            
        end
    end
    
end
