#include <deque>
#include <mutex>
#include <condition_variable>
#include <unistd.h>
 
//! \brief A templated *thread-safe* collection based on dequeue
//!
//!        pop_front() waits for the notification of a filling method if the collection is empty.
//!        The various "emplace" operations are factorized by using the generic "addData_protected".
//!        This generic asks for a concrete operation to use, which can be passed as a lambda.
template< typename T >
class TQueueConcurrent {
 
    using const_iterator = typename std::deque<T>::const_iterator;
 
public:
    //! \brief Emplaces a new instance of T in front of the deque
    template<typename... Args>
    void emplace_front( Args&&... args )
    {
        addData_protected( [&] {
            _collection.emplace_front(std::forward<Args>(args)...);
        } );
    }
 
    //! \brief Emplaces a new instance of T at the back of the deque
    template<typename... Args>
    void emplace_back( Args&&... args )
    {
        addData_protected( [&] {
            _collection.emplace_back(std::forward<Args>(args)...);
        } );
    }
 
    //! \brief Returns the front element and removes it from the collection
    //!
    //!        No exception is ever returned as we garanty that the deque is not empty
    //!        before trying to return data.
    T pop_front( void ) noexcept
    {
        std::unique_lock<std::mutex> lock{_mutex};
        while (_collection.empty()) {
            _condNewData.wait(lock);
        }
        auto elem = std::move(_collection.front());
        _collection.pop_front();
        return elem;
    }
 
    void pop_front(T &dest ) noexcept
    {
        std::unique_lock<std::mutex> lock{_mutex};
        while (_collection.empty()) {
            _condNewData.wait(lock);
        }
        dest = std::move(_collection.front());
        _collection.pop_front();
        return;
    }
    
    
     void clear( void ) noexcept
    {

        _collection.clear();
    }
 
    int32_t size(void )
    {
        return(_collection.size());
    }
 
private:
 
    //! \brief Protects the deque, calls the provided function and notifies the presence of new data
    //! \param The concrete operation to be used. It MUST be an operation which will add data to the deque,
    //!        as it will notify that new data are available!
    template<class F>
    void addData_protected(F&& fct)
    {
        std::unique_lock<std::mutex> lock{ _mutex };
        fct();
        lock.unlock();
        _condNewData.notify_one();
    }
 
    std::deque<T> _collection;                     ///< Concrete, not thread safe, storage.
    std::mutex   _mutex;                    ///< Mutex protecting the concrete storage
    std::condition_variable _condNewData;   ///< Condition used to notify that new data are available.
};










#include <string.h>
#define MAX_pFIFO_MESSAGE_SIZE 8192

template <class T>
class pFIFO {
public:
	typedef struct
	{
        uint16_t len; 
		char msgBuf[MAX_pFIFO_MESSAGE_SIZE];
	}Msg; 
	
	Msg msg;
    Msg rxmsg;
   string qname= "Unnamed";
   TQueueConcurrent<T> data;
   TQueueConcurrent<Msg> m_data;

 
    void setName(string _qname)
    {
        qname=_qname;
    }

  

       int8_t m_writeFifo(char* Buf, size_t len)
    {
     
    
        msg.len = len; 
    	memcpy(msg.msgBuf,Buf,len);
        m_data.emplace_back(msg);
       
        return 1;
    }

    int8_t m_readFifo(char *Buf) 
    {
    
        rxmsg=m_data.pop_front();
        memcpy(Buf,rxmsg.msgBuf,rxmsg.len);

        return 1;                
    }

    bool filter(std::string localString)
    {
    	for(char& c : localString) {
    	   if ((c < 32) || c > 126 ) 
    	   {
    		   if( c == 0)
    			   return 1;
    		   else
    			   
    		   return 0;
    		  
    	   }
    	   	 
    		 
    	}
    	return 1;
    }
    

        
    uint32_t m_getFifoCount(){
        return m_data.size();
    }
    void reset()
    {
        data.clear();
        m_data.clear();
    }
    };


