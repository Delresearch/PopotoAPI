//
//  TCPCmdClient.hpp
//  popoto_client
//
//  Created by James DellaMorte on 5/9/19.
//  Copyright © 2019 James DellaMorte. All rights reserved.
//

#ifndef TCPCmdClient_hpp
#define TCPCmdClient_hpp


#include "TCPClient.hpp"
#include <queue>
#include <mutex>

class TCPCmdClient:public TCPClient {
private:
    string replyStr;
    mutex  replyQMutex;
    queue <string> replyQ;
    
public:
    TCPCmdClient():TCPClient(1)
    {
        replyStr ="";
    }
    
    TCPCmdClient(string host, int port):TCPClient(1)
    {
        replyStr ="";
        conn(host , port);
    }
    
    
    bool SendCommand(string Command)
    {
        string cmd, args, JsonCmd;
        string delimiter = " ";
        size_t pos = 0;
        
        pos = Command.find(delimiter);
        
        
        cmd = Command.substr(0, pos);
        Command.erase(0, pos + delimiter.length());
        args = Command;
        if(strlen(args.c_str()) == 0)
        {
            args =" Unused Arguments";
        }
            
        
        JsonCmd ="{ \"Command\": \"" + cmd + "\", \"Arguments\": \""+args + "\"}\n";
         
        return (send_data((char *) JsonCmd.c_str(), (int) strlen(JsonCmd.c_str())));
    }
    int getReply(string *rep)
    {
        int count = 0;
        std::unique_lock<std::mutex> lock(replyQMutex);
        if(replyQ.size() > 0)
        {
            *rep = replyQ.front();
            replyQ.pop();
            count = 1;
        }
        lock.unlock();
    
        return(count);
    }
    
    virtual void processRxMessage(char *Msg, int len)
    {
        int i; 
        for(i = 0; i < len; i++)
        {
           
            if(Msg[i] == 13)
            {
                std::unique_lock<std::mutex> lock(replyQMutex);
                replyQ.push(replyStr);
                lock.unlock();
                
                replyStr = "";
            }
            else{
                replyStr.append(&Msg[i], 1);
            }
        }
    }
    
    
};


#endif /* TCPCmdClient_hpp */
