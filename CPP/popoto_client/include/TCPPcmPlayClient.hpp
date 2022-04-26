//
//  TCPPcmPlayClient.hpp
//  popoto_client
//
//  Created by James DellaMorte on 5/10/19.
//  Copyright © 2019 James DellaMorte. All rights reserved.
//

#ifndef TCPPcmPlayClient_hpp
#define TCPPcmPlayClient_hpp

#include "TCPClient.hpp"
#define POPOTO_PCM_FS 102400


class TCPPcmPlayClient:public TCPClient {
private:
    void (*RxCallBack)(void *,void *,int);
    int PcmLen;
    int PcmByteLen;
    float *PcmSendBuf;
     
public:
    TCPPcmPlayClient(string host, int port,  int PCMFrameLen):TCPClient(PCMFrameLen)
    {
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
    
    
    bool Send(void *Pcm)
    {
        memcpy(PcmSendBuf, Pcm, PcmByteLen);
        return (send_data((char *) PcmSendBuf, PcmByteLen));
    }
    
    
   
    
    virtual void processRxMessage(char *Msg, int len)
    {
    
    }
    
};



#endif /* TCPPcmClient_hpp */
