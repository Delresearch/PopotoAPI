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

popoto_client *popoto0;

void PlayPCM(string host0, int port0, string filename, float Gain);


/*  Popoto0PCMHandler
 *  Callback for Popoto channel 0 recording pcm over ethernet.
 *  This function gets called every 6.25mS.
 *  The simple example below records pcm queue to a file.
 */
void Popoto0PCMHandler(void *Pcm, int Len)
{
    FILE *fp = (FILE *)fpOut0;
    popotoPCMPacket pcmPkt;

    if (Len != sizeof(pcmPkt)) cout << "Error in PcmHandler" << endl;

    for (int i = 0; i < sizeof(pcmPkt.Pcm) / sizeof(float); i++)
    {
        popotoPCMPacket *p = (popotoPCMPacket *)Pcm;
        float ftmp = p->Pcm[i] * p->Pcm[i];
        if (ftmp < 100) Eng += ftmp;
    }
    EngCount += sizeof(pcmPkt.Pcm) / sizeof(float);

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
        printf("Use:  %s <ip address Modem >  <port address Modem>  <PCM filename> <gain>\n", argv[0]);
        exit(-1);
    }
    host = argv[1];
    string portstr = argv[2];
    port = stoi(portstr);

    string filename = argv[3];
    Gain = atof(argv[4]);

    PlayPCM(host, port, filename, Gain);

    return 0;
}

/**
 *
 */
void PlayPCM(string host0, int port0, string filename, float Gain)
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

            if (p0Reply.find("StopPlayingSuccess") != string::npos)
            {
                done |= 3;
                cout << "Test Completed " << endl;
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
    exit(0);
}

