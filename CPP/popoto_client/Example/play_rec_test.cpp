//
//  main.cpp
//  popoto_client
//
//  Created by James DellaMorte on 5/9/19.
//  Copyright �� 2019 James DellaMorte. All rights reserved.
//
#include <cstdlib>
#include <iostream>
#include <string>
#include <math.h>
#include <time.h>
#include "popoto_client.hpp"
#include "play_record_utils.h"


volatile int TxModeEnabled = 0;
void PlayRecModemTest( string filename, int mode, int numTests);

volatile FILE *fpOut0=NULL;
volatile FILE *fpOut1=NULL;

volatile int pegCount = 0;
volatile float Eng;
volatile uint32_t EngCount;
float Gain=1; 

popoto_client *popoto0, *popoto1;

void Popoto1PCMHandler(void *Pcm, int Len)
{
    FILE *fp = (FILE *)fpOut1;
    popotoPCMPacket pcmPkt;
    
    if (Len != sizeof(pcmPkt))
        cout << "Error in PcmHandler" << endl;
    if(fp != NULL)
    {
        while (popoto1->pcmInQ.size() > 0)    
        {
            popoto1->pcmInQ.pop_front(pcmPkt);
            fwrite((void *)&pcmPkt.Pcm[0], sizeof(float), sizeof(pcmPkt.Pcm)/sizeof(float), fp);
        }
    }
}


void Popoto0PCMHandler(void *Pcm, int Len)
{
    FILE *fp = (FILE *)fpOut0;
    popotoPCMPacket pcmPkt;
    
    if (Len != sizeof(pcmPkt)) 
        cout << "Error in PcmHandler" << endl;
    if(fp != NULL)
    {
        while (popoto0->pcmInQ.size() > 0)
        {
            popoto0->pcmInQ.pop_front(pcmPkt);
            fwrite((void *)&pcmPkt.Pcm[0], sizeof(float), sizeof(pcmPkt.Pcm)/sizeof(float), fp);
        }
    }
    for(int i = 0; i < sizeof(pcmPkt.Pcm)/sizeof(float); i++)
    {   
        popotoPCMPacket *p = (popotoPCMPacket *) Pcm;
        float ftmp = p->Pcm[i] * p->Pcm[i];
        if(ftmp < 100 )
            Eng += ftmp;
    }
    EngCount += sizeof(pcmPkt.Pcm)/sizeof(float); 
    
    pegCount++;
    
    
}




/*  Simple example main to connect to */


int main(int argc, const char *argv[])
{
    // insert code here...
    int port0;
    string host0;
    int NumberOfIterations = 2;
    
    if (argc < 7)
    {
        printf("Use:  %s <ip address Modem 1>  <port address Modem1>  <ip address Modem2>  <port address Modem2>  <gain>  <temporary PCM filename>\n", argv[0]);
        exit(-1);
    }
    host0 = argv[1];
    string portstr = argv[2];
    port0 = stoi(portstr);
    

        string host1 = argv[3];
        string portstr1 = argv[4];
        int port1 = stoi(portstr1);
        Gain = atof(argv[5]);
        string filename = argv[6];

    popoto0 =
        new popoto_client(host0, port0, Popoto0PCMHandler);  //  Initialize with the IP, port and PCM callback routine.
    popoto1 =
        new popoto_client(host1, port1, Popoto1PCMHandler);  //  Initialize with the IP, port and PCM callback routine.

#if 0
    
    // Set play and record to Baseband mode and retest
    popoto0->SetValue("PlayMode", 1);
    popoto0->SetValue("RecordMode", 1);
    popoto1->SetValue("PlayMode", 1);
    popoto1->SetValue("RecordMode", 1);

    popoto0->WaitForResponse("RecordMode", 5000); // Make sure that we've set the modes (wait for up to 5000mS)
    popoto1->WaitForResponse("RecordMode", 5000);


    cout << " ---------------    Test the Play and record Baseband NETWORK_STREAMING_MODE Mode ------------------------" << endl;
    PlayRecModemTest( filename+"BB", NETWORK_STREAMING_MODE,NumberOfIterations);
    cout << " ---------------    Test the Play and record Baseband file Mode ------------------------" << endl;
    PlayRecModemTest( filename+"BB", PLAY_FILE_MODE,NumberOfIterations);
#endif


    //set play and record to passband Mode
    popoto0->SetValue("PlayMode", 0);
    popoto0->SetValue("RecordMode", 0);
    popoto1->SetValue("PlayMode", 0);
    popoto1->SetValue("RecordMode", 0);

    cout << " ---------------    Test the Play and record NETWORK_STREAMING_MODE Mode ------------------------" << endl;
    PlayRecModemTest(filename, NETWORK_STREAMING_MODE, NumberOfIterations);
    cout << " ---------------    Test the Play and record file Mode ------------------------" << endl;
    PlayRecModemTest(filename, PLAY_FILE_MODE,NumberOfIterations);

       
    
    
    
    
    
    return 0;
}
void PlayRecModemTest(string filename, int Play_Record_mode, int numTests)
{
    string filename0 = filename +"0";
    string filename1 = filename +"1";
    FILE *fp;
    int GoodCount=0, BadCount = 0;
   
    
    if(popoto0->cmd->isConnected() && popoto1->cmd->isConnected())
    {
        int firstCall;
        string p1Reply;
        string p0Reply;
        string TemplateFilename;
        int done = 0;
        sleep(1);
        popoto0->SendCommand("Event_StartRx");
        popoto1->SendCommand("Event_StartRx");

        Eng = 0; EngCount = 0; 
        int status = StartRecord(popoto0, &fpOut0, filename0, Play_Record_mode);
        
        if (Play_Record_mode == NETWORK_STREAMING_MODE)
        {
            // If we are in network mode, we just use the requested filename
            
            TemplateFilename = filename0;
        }
        if (status == SUCCESS)
        {
            sleep(1);  // Wait for a second so file has some leading silence
            
            popoto1->SendCommand("SetValue PayloadMode 1 0"); // Set the rate to 10240
            
            popoto1->SendCommand("SetValue TxPowerWatts 40 0");  // Transmit 2 watts
            
            cout << "P1: *******   Sending a test Packet **********" << endl;
            popoto1->SendCommand("Event_sendTestPacket");   //  Transmit a test message
            
            done = 0;
            while(!done)
            {
                if(popoto1->getReply(&p1Reply))
                {
                    cout << "P1: " << p1Reply << endl;
                }
                if(popoto0->getReply(&p0Reply))
                {
                    cout << "P0: " << p0Reply<< endl;
                }
                if (Play_Record_mode != NETWORK_STREAMING_MODE)
                {
                    if (p0Reply.find("Recording to") != string::npos)
                    {
                        TemplateFilename = p0Reply.substr(p0Reply.find("Recording to ") + strlen("Recording to "));
                        TemplateFilename = TemplateFilename.substr(0, TemplateFilename.find("\""));
                        cout << "P0: ***********Recording to " << TemplateFilename << "\n";
                    }
                }
                if(p0Reply.find("Timeout") != string::npos)
                {
                    done = -1;
                }
                if(p0Reply.find("Data") != string::npos)
                {
                    done =1;
                }
                if(p1Reply.find("CRCError") != string::npos)
                {
                    done = -1;
                }
                usleep(.1*1e6);
            }
            
            cout << " *******   Waiting **********" << endl;

          
            StopRecord(popoto0, &fpOut0, Play_Record_mode);
  //          StartRecord(popoto1, &fpOut1, filename1, Play_Record_mode);
            popoto0->SendCommand("Event_StartRx");
            popoto1->SendCommand("Event_StartRx");

            for (int j = 0; j< numTests; j++)
            {
                
                cout << " ******* Transmitting Recorded file  P0->P1 Iteration " << j << " **********" << endl;
                     
                StartPlay(popoto0, TemplateFilename, Gain, Play_Record_mode);
               
                done = 0;
                cout << " *******   Waiting For Data **********" << endl;
                time_t timer;
                time(&timer);  /* get current time; same as: timer = time(NULL)  */

                while((done & 0x3) != 3)
                {
                        
                    

                    
                    
                    usleep(100000);
                    p1Reply="";
                    p0Reply = "";
                    if(popoto1->getReply(&p1Reply))
                    {
                        cout << "P1: " << p1Reply << endl << std::flush;
                    }
                    if(popoto0->getReply(&p0Reply))
                    {
                        cout << "P0: " << p0Reply << endl << std::flush;
                    }
                    if(p0Reply.find("Timeout") != string::npos)
                    {
                        done |=1;
                    }
                   
                    if(p1Reply.find("CRCError") != string::npos)
                    {
                        BadCount ++;
                        done |= 1;
                    }
                    if(p1Reply.find("Data") != string::npos)
                    {
                        done |= 1;
                        GoodCount++;
                    }
                    if(p0Reply.find("StopPlayingSuccess") != string::npos)
                    {
                        done |= 2;
                       
                    }

                    time_t now;
                    
                    time(&now);
                    double seconds = difftime(now,timer);
                    if(seconds > 30)
                    {
                        done |=3;
                        BadCount++;
                    }
                    


                }
                cout << "******* Test In Progress Good Receptions " << GoodCount << " Bad Receptions " << BadCount
                     << endl
                     << std::flush;
            }
        }
        
    }
    
    
    cout << "Test Complete Good Receptions " << GoodCount << " Bad Receptions " << BadCount << endl;
    
 //   StopRecord(popoto1, &fpOut1, Play_Record_mode);   
    
    
}
