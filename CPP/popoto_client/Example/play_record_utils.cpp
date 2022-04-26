#include "popoto_client.hpp"
#include "play_record_utils.h"

#define NUM_SAMPS_PERSEND (640 * 300)

float tempBuf[NUM_SAMPS_PERSEND];

int StartPlay(popoto_client *popoto, string filename, float Gain, int Mode)
{
    FILE *fp;
    
    int firstCall;
    switch (Mode)
    
    {
        case NETWORK_STREAMING_MODE:
        {
            fp = fopen(filename.c_str(), "rb");
            if (fp != NULL)
            {
            }
            int32_t count;
            firstCall = 1;
            int PlayStarted = 0;
            while ((count = (int32_t)fread(tempBuf, sizeof(float), NUM_SAMPS_PERSEND, fp)) > 0)
            {
                popoto->SendPcmVector(tempBuf, Gain, count, firstCall);

                firstCall = 0;
            }
        }
        break;
        case PLAY_FILE_MODE:
            popoto->SendCommand("StartPlaying " + filename + " " + std::to_string(Gain));
            break;
    }
}

int StopRecord(popoto_client *popoto, volatile FILE **fp, int Mode)
{
    switch (Mode)
    {
        case NETWORK_STREAMING_MODE:
        {
            FILE *lfp = (FILE *)*fp;
            *fp = NULL;
            if (lfp != NULL) fclose(lfp);
        }
        break;
        case RECORD_FILE_MODE:
            popoto->SendCommand("StopRecording ");
            break;
    }
    return SUCCESS;
}
int StartRecord(popoto_client *popoto, volatile FILE **fp, string filename, int Mode)
{
    switch (Mode)
    {
        case NETWORK_STREAMING_MODE:

            *fp = fopen(filename.c_str(), "wb");
            if (*fp == NULL)
            {
                return FAILURE;
            }
            break;
        case RECORD_FILE_MODE:
            popoto->SendCommand("StartRecording " + filename);

            break;
    }
    return SUCCESS;
}
