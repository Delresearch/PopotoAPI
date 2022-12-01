#include "popoto_client.hpp"
#include "play_record_utils.h"
#include "WavProcess.h"
#define NUM_SAMPS_PERSEND (640 * 300)
#define HEADER_SIZE 58
float tempBuf[NUM_SAMPS_PERSEND];
WavProcess wavProcess;
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
            std::pair<int,int> filedata = wavProcess.getSampleData(fp);
			int header_size = filedata.first;
			int data_len = filedata.second;
			std::cout << header_size << " " << data_len << std::endl;

			fseek(fp, header_size+data_len, SEEK_SET);
	//		ftruncate(File, (header_size+data_len)); //TODO: Truncate the metadata off of the wav file
			fseek(fp, header_size, SEEK_SET);
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

int StopRecord(popoto_client *popoto, FILE **fp, int Mode)
{
    switch (Mode)
    {
        case NETWORK_STREAMING_MODE:
        {
            FILE *lfp = (FILE *)*fp;
            *fp = NULL;
            fseek(lfp, 0, SEEK_END);
            uint32_t datasize = ftell(lfp) - HEADER_SIZE;
            fseek(lfp, HEADER_SIZE-4, SEEK_SET); // Write file data size to header of wav file
            fwrite(&datasize, 4, 1, lfp);
            fseek(lfp, 0, SEEK_END);
            if (lfp != NULL) fclose(lfp);
        }
        break;
        case RECORD_FILE_MODE:
            popoto->SendCommand("StopRecording ");
            break;
    }
    return SUCCESS;
}
int StartRecord(popoto_client *popoto, FILE **fp, string filename, int Mode)
{
    switch (Mode)
    {
        case NETWORK_STREAMING_MODE:

            *fp = fopen(filename.c_str(), "wb");
            wavProcess.generateHeader(*fp);
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
