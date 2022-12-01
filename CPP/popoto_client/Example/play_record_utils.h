/**
*/

#ifndef PLAY_RECORD_UTILS_H
#define PLAY_RECORD_UTILS_H

enum
{
    NETWORK_STREAMING_MODE = 0,
    RECORD_FILE_MODE = 1,
    PLAY_FILE_MODE = 1
};

enum
{
    SUCCESS,
    FAILURE
};

int StartRecord(popoto_client *popoto,  FILE **fp, string filename, int Mode);
int StopRecord(popoto_client *popoto,  FILE **fp, int Mode);
int StartPlay(popoto_client *popoto, string filename, float Gain, int Mode);


#endif