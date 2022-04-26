//
//  TCPClient.hpp
//  popoto_client
//
//  Created by James DellaMorte on 5/9/19.
//  Copyright © 2019 James DellaMorte. All rights reserved.
//

#ifndef TCPClient_hpp
#define TCPClient_hpp

#include <stdio.h>
#include <string>
#include <iostream>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <thread>
#include <unistd.h>
#include <queue>




using namespace std;

class TCPClient
{
private:
    volatile int sock;
    std::string address;
    int port;
    struct sockaddr_in server;
    int ReadCount;
    char *replyStr;
    thread *TCPthread;
    
public:
    volatile int doneProcessing;
    
    TCPClient(int readLen)
    {
        sock = -1;
        port = 0;
        address = "";
        doneProcessing = 0;
        ReadCount = readLen;
        replyStr = new char[ReadCount]();
        TCPthread = new thread(&TCPClient::TCPRxLoop, this);
        
    }
    ~TCPClient()
    {
        doneProcessing =1; 
        disconnect();
        TCPthread->join();
        delete replyStr;
    }
    bool conn(string address , int port)
    {
        //create socket if it is not already created
        if(sock == -1)
        {
            //Create socket
            sock = socket(AF_INET , SOCK_STREAM , 0);
            if (sock == -1)
            {
                perror("Could not create socket");
            }
            
            cout<<"Socket created\n";
        }
        else    {    /* OK , nothing */    }
        
        //setup address structure
        if(inet_addr(address.c_str()) == -1)
        {
            struct hostent *he;
            struct in_addr **addr_list;
            
            //resolve the hostname, its not an ip address
            if ( (he = gethostbyname( address.c_str() ) ) == NULL)
            {
                //gethostbyname failed
                herror("gethostbyname");
                cout<<"Failed to resolve hostname\n";
                
                return false;
            }
            
            //Cast the h_addr_list to in_addr , since h_addr_list also has the ip address in long format only
            addr_list = (struct in_addr **) he->h_addr_list;
            
            for(int i = 0; addr_list[i] != NULL; i++)
            {
                //strcpy(ip , inet_ntoa(*addr_list[i]) );
                server.sin_addr = *addr_list[i];
                
                cout<<address<<" resolved to "<<inet_ntoa(*addr_list[i])<<endl;
                
                break;
            }
        }
        
        //plain ip address
        else
        {
            server.sin_addr.s_addr = inet_addr( address.c_str() );
        }
        
        server.sin_family = AF_INET;
        server.sin_port = htons( port );
        
        //Connect to remote server
        if (connect(sock , (struct sockaddr *)&server , sizeof(server)) < 0)
        {
            perror("connect failed. Error");
            return 1;
        }
        
        cout<<"Connected\n";
        return true;
    }
    
    void disconnect()
    {
        if(isConnected())
        {
            int tmpSock = sock;
            sock = -1;
            close(tmpSock);
            
        }
    }
    
    bool send_data(char *data, int len)
    {
        //Send some data
        if( send(sock , data , len, 0) != len)
        {
            perror("Send failed : ");
            return false;
        }
        
        return true;
    }
    int receive(char *reply, ssize_t size=512)
    {
        int replyLen=0;
        

            //Receive a reply from the server
        while( (replyLen = (int) recv(sock , reply , size , MSG_WAITALL)) < 0)
        {
            usleep(10000);
        }
        
       
        return (int) replyLen;
    }
    
    bool isConnected()
    {
        return(sock != -1);
    }
    
    virtual void processRxMessage(char *Msg, int len)=0;
    
    void TCPRxLoop() {
        
        int rxCount;
        
        /*
         * main loop: wait for a connection request, echo input line,
         * then close connection.
         */
        while (!doneProcessing)
        {
            /*
             * accept: wait for a connection request
             */
            if(sock ==-1)
            {
                usleep(10000);
            }
            else
            {
                if((rxCount = receive(replyStr,ReadCount)) > 0)
                {
                    processRxMessage(replyStr, rxCount);
                }
            }
  
            
            
        }
    }
    
};


#endif /* TCPClient_hpp */
