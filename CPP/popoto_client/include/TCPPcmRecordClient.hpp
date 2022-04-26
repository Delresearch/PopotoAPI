//
//  TCPPcmRecordClient.hpp
//  popoto_client
//
//  Created by James DellaMorte on 5/10/19.
//  Copyright © 2019 James DellaMorte. All rights reserved.
//

#ifndef TCPPcmRecordClient_hpp
#define TCPPcmRecordClient_hpp

#include "TCPClient.hpp"
#define POPOTO_PCM_FS 102400


class TCPPcmRecordClient:public TCPClient {
private:
    void (*RxCallBack)(void *,void *,int);
    int PcmLen;
    int PcmByteLen;
    float *PcmSendBuf;
    void *PCMCallBackArg = NULL;
public:
    TCPPcmRecordClient(string host, int port, void (*RxPcmCallback)(void *, void *, int), void * Arg, int PCMFrameLen):TCPClient(PCMFrameLen)
    {
        PCMCallBackArg = Arg;
        RxCallBack =  RxPcmCallback; 
        PcmLen = PCMFrameLen;
        PcmByteLen = PCMFrameLen;
        PcmSendBuf= new float [PCMFrameLen]();
        if(PcmSendBuf == NULL)
        {
            cout << "ERROR" << endl; ;
        }
        else
        {
            conn(host , port);
        }
    }
    
    

   
    
    virtual void processRxMessage(char *Msg, int len)
    {
        if(len != PcmLen)
        {
            printf(" **************** ALERT *************\n");
        }
       
        if(RxCallBack != NULL)
        {
            RxCallBack(PCMCallBackArg, Msg, PcmLen);
        }
    }
    
};



#endif /* TCPPcmClient_hpp */
