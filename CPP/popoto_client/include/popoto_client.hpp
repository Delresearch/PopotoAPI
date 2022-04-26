//
//  popoto_client.hpp
//  popoto_client
//
//  Created by James DellaMorte on 5/9/19.
//  Copyright © 2019 James DellaMorte. All rights reserved.
//

#ifndef popoto_client_hpp
#define popoto_client_hpp

#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "TCPCmdClient.hpp"
#include "TCPPcmPlayClient.hpp"
#include "TCPPcmRecordClient.hpp"
#include "pFIFO.h"

enum {
    POPOTO_RATE_80,
    POPOTO_RATE_5120,
    POPOTO_RATE_2560,
    POPOTO_RATE_1280,
    POPOTO_RATE_640,
    POPOTO_RATE_10240,
};

#define SEND_PCM_LATENCY 300

#define popoto_FS   102400
#define popoto_PCM_FRAME_LEN (640)

typedef struct
{
    float   status1;
    float   status2;
    float    Pcm[popoto_PCM_FRAME_LEN];
}popotoPCMPacket;


class popoto_client{
    
public:
    TQueueConcurrent <popotoPCMPacket> pcmOutQ;
    TQueueConcurrent <popotoPCMPacket> pcmInQ;
    void (*RxPcmCallback)(void *, int);
    int LatencySent;
    int done_processing;
    thread *Playthread;

    popoto_client(string host, int basePort, void (*_RxPcmCallback)(void *, int) )
    {
        RxPcmCallback = _RxPcmCallback; 
        cmd = new TCPCmdClient(host, basePort);
        pcmRecord = new TCPPcmRecordClient(host, basePort+2,  popoto_client::PcmCallback, this,  sizeof(popotoPCMPacket));
        pcmPlay = new TCPPcmPlayClient(host, basePort+5, sizeof(popotoPCMPacket));
        LatencySent = 0;
        done_processing = false;
        Playthread = new thread(&popoto_client::SendPcmThread, this);

    }
    ~popoto_client()
    {
        cmd->doneProcessing = true;
        pcmPlay->doneProcessing = true;\
        
        pcmRecord->doneProcessing = true;
        sleep(10);
        delete cmd;
        delete pcmRecord;
        delete pcmPlay;
    }
    
    int getReply(string *rep)
    {
        return(cmd->getReply(rep));
    }
    
    
    bool SendCommand(string Command)
    {
        return(cmd->SendCommand(Command));
    }
    
    void GetValue(string Element)
    {
        string cmd = "GetValue " + Element + " int 0";
        SendCommand(cmd);
    }
    
    void SetValue(string Element, float Value)
    {
        string cmd = "SetValue ";
        cmd +=  Element;
        cmd += " int ";
        cmd += std::to_string(Value);
        cmd += " 0";
        SendCommand(cmd);
    }
    string WaitForResponse(string matchString, uint32_t timeoutMS)
    {
        int done = 0;
        int TimeCounter = 0;
        string reply="";
        
        while((reply.find(matchString) == string::npos) && (TimeCounter < timeoutMS))
        {
            getReply(&reply);
            
            usleep(5000);
            TimeCounter +=5;
        }
        
        if(TimeCounter >= timeoutMS)
            reply = "TIMEOUT";
        return reply;
    }
    
    bool SendPcmVector(float *Pcm, float Scale, float Length, int firstCall)
    {
        popotoPCMPacket pcmPkt;
        pcmPkt.status1 = Scale;
        pcmPkt.status2 = Scale;
        
        if(Length <= 0 )
            return(1);
        
        if(firstCall)
        {
            LatencySent = 0;
            pcmOutQ.clear();
            
            
        }
     
        while (Length > 0 )
        {
            for(int i = 0; i < popoto_PCM_FRAME_LEN; i++)
            {
                if(Length -- > 0)
                    pcmPkt.Pcm[i] = *Pcm++;
                else
                    pcmPkt.Pcm[i] = 0.0;
            }
            
            pcmOutQ.emplace_back(pcmPkt);
        }
        
      
        
        return(0);
    }

    static void PcmCallback(void *Arg, void *PcmIn, int Len);
    
    int SendPcmThread()
    {
        int retval = 0;
        int SentCount = 0;
        
        while(!done_processing)
        {
            if(pcmOutQ.size() >0)
            {
                if(LatencySent == 0)
                {
                    cout << "Sending StartNetPlay " << endl;
                    SendCommand("StartNetPlay ");
                    WaitForResponse("Play Started", 5000);
                    
                    
                }
                LatencySent ++;
                popotoPCMPacket pcmPkt;
               
                pcmOutQ.pop_front(pcmPkt);
                while(!pcmPlay->Send(&pcmPkt))
                {
                    usleep(1000);
                }
                 
               // cout << "Sent: " << SentCount++ << endl;
            }
            else
            {
                usleep( .005* 1e6);
            }
//            if(LatencySent > 300)
//                usleep( .006* 1e6);
        }
        return retval;
    }
    
    
    TCPPcmPlayClient *pcmPlay;
    TCPPcmRecordClient *pcmRecord;
    
    TCPCmdClient *cmd;
};
#endif /* popoto_client_hpp */
