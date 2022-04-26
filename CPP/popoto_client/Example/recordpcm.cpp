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


volatile FILE *fpOut0 = NULL;

volatile int pegCount = 0;
volatile float Eng;
volatile uint32_t EngCount;
volatile uint32_t doneRecording = 0; 

float duration = 10* 102400; 

popoto_client *popoto0;

void RecordPCM(string host0, int port0, string filename, float Gain);


/*  Popoto0PCMHandler
 *  Callback for Popoto channel 0 recording pcm over ethernet.
 *  This function gets called every 6.25mS.
 *  The simple example below records pcm queue to a file.
 */
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
            duration -= Len/sizeof(float); 

            if(duration <= 0)
            {
                doneRecording = 1; 

            }
        }
    }
 
    pegCount++;
}

/*
Invoke the Tests after parsing arguments  */

int main(int argc, const char *argv[])
{
    // insert code here...
    int port;
    string host;
    float Gain; 

    if (argc < 5)
    {
        printf("Use:  %s <ip address Modem >  <port address Modem>  <PCM filename> <duration in seconds>\n", argv[0]);
        exit(-1);
    }
    host = argv[1];
    string portstr = argv[2];
    port = stoi(portstr);

    string filename = argv[3];
    duration = atof(argv[4]) * popoto_FS;

    RecordPCM(host, port, filename, duration);

    return 0;
}

/**
 *
 */
void RecordPCM(string host0, int port0, string filename, float Gain)
{
    FILE *fp;

    popoto0 =
        new popoto_client(host0, port0, Popoto0PCMHandler);  //  Initialize with the IP, port and PCM callback routine.
    
    if (popoto0->cmd->isConnected())
    {
        int firstCall;
        string p0Reply;
        int done = 0;
        
        float Timeout = 60;

        // filename0 = "/Users/jim/Downloads/tone.pcm";
        cout << " ******* Transmitting  file " << filename;

        cout << "Using a gain of " << Gain << " **********" << endl;

        StartPlay(popoto0, filename, Gain, NETWORK_STREAMING_MODE);

        done = 0;
        cout << " *******   Waiting For Completion or " << Timeout << " Second Timeout **********" << endl;
        time_t timer;
        time(&timer); /* get current time; same as: timer = time(NULL)  */

        while ((done & 0x3) != 3)
        {
            usleep(100000);
            p0Reply = "";
            if (popoto0->getReply(&p0Reply))
            {
                cout << "Modem Response: " << p0Reply << endl << std::flush;
            }

            if(doneRecording != 0)
            {
                done = 0x3; 
            }
            time_t now;

            time(&now);
            double seconds = difftime(now, timer);
            if (seconds > Timeout)
            {
                done |= 3;
                cout << "Test Completed due to Timeout" << endl;
            }
        }
    }
    fclose((FILE *) fpOut0);
    exit(0);
}

