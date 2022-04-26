//
//  popoto_client.cpp
//  popoto_client
//
//  Created by James DellaMorte on 5/9/19.
//  Copyright © 2019 James DellaMorte. All rights reserved.
//

#include "popoto_client.hpp"



void popoto_client::PcmCallback(void *Arg, void *PcmIn, int Len)
{
    popoto_client *obj = (popoto_client *) Arg;
    popotoPCMPacket *pkt = (popotoPCMPacket *) PcmIn;
    
    if(obj != NULL)
    {
        
        
        if(obj->RxPcmCallback != NULL)
        {
            obj->pcmInQ.emplace_back(*pkt);
            obj->RxPcmCallback(PcmIn, Len);
        }
    }
}
