'''
Created on Oct 12, 2016

@author: mwitt_000
'''

import queue
import threading


## wrapper class for a queue of packets
class Interface:
    ## @param maxsize - the maximum size of the queue storing packets
    def __init__(self, maxsize=0):

        self.queue = queue.Queue(maxsize);
        self.mtu = None
    
    ##get packet from the queue interface
    def get(self):
        try:
            return self.queue.get(False)
        except queue.Empty:
            return None
        
    ##put the packet into the interface queue
    # @param pkt - Packet to be inserted into the queue
    # @param block - if True, block until room in queue, if False may throw queue.Full exception
    def put(self, pkt, block=False):
        self.queue.put(pkt, block)
        
## Implements a network layer packet (different from the RDT packet 
# from programming assignment 2).
# NOTE: This class will need to be extended to for the packet to include
# the fields necessary for the completion of this assignment.


class NetworkPacket:
    ## packet encoding lengths 
    dst_addr_S_length = 5
    endFlag_length = 1
    
    ##@param dst_addr: address of the destination host
    # @param data_S: packet payload
    #@para endflag: determine if packet segment is the last one
    def __init__(self, dst_addr, data_S, endFlag):
        self.dst_addr = dst_addr
        self.data_S = data_S
        self.endFlag = endFlag
        
    ## called when printing the object
    def __str__(self):
        return self.to_byte_S()
        
    ## convert packet to a byte string for transmission over links
    def to_byte_S(self):
        byte_S = str(self.dst_addr).zfill(self.dst_addr_S_length)
        byte_S += str(self.endFlag)
        byte_S += self.data_S

        return byte_S
    
    ## extract a packet object from a byte string
    # @param byte_S: byte string representation of the packet
    @classmethod
    def from_byte_S(self, byte_S):
        dst_addr = int(byte_S[0 : NetworkPacket.dst_addr_S_length])
        endFlag = int(byte_S[NetworkPacket.dst_addr_S_length:NetworkPacket.dst_addr_S_length+1 ])
        data_S = byte_S[ NetworkPacket.dst_addr_S_length + 1: ]

        return self(dst_addr, data_S, endFlag)

    

## Implements a network host for receiving and transmitting data
class Host:
    # for segmentation
    wholePacket = ""
    
    ##@param addr: address of this node represented as an integer
    def __init__(self, addr):
        self.addr = addr
        self.in_intf_L = [Interface()]
        self.out_intf_L = [Interface()]
        self.stop = False #for thread termination
    
    ## called when printing the object
    def __str__(self):
        return 'Host_%s' % (self.addr)
       
    ## create a packet and enqueue for transmission
    # @param dst_addr: destination address for the packet
    # @param data_S: data being transmitted to the network layer
    def udt_send(self, dst_addr, data_S):

        nonData = 8
        packet = []

        #check if length of data sent is
        if len(data_S) + nonData> self.out_intf_L[0].mtu:

            while len(data_S) + nonData > self.out_intf_L[0].mtu:

                #copy portion of packet of size mtu
                dataPiece = data_S[:self.out_intf_L[0].mtu-nonData]

                #cutting portion off original data
                data_S = data_S[self.out_intf_L[0].mtu-nonData:]

                #save to be sent later
                packet.append(NetworkPacket(dst_addr,dataPiece,0))

        #add piece of packet that is appropriate length
        packet.append(NetworkPacket(dst_addr, data_S,1))

        for p in packet:
            print('%s: sending packet "%s" out interface with mtu=%d' % (self, p, self.out_intf_L[0].mtu))
            self.out_intf_L[0].put(p.to_byte_S())  # send packets always enqueued successfully

        
    ## receive packet from the network layer
    def udt_receive(self):

        #receive the packet from interface 0
        pkt_S = self.in_intf_L[0].get()

        #check if interface is not empty
        if pkt_S is not None:

            #add segment to whole message minus the non data
            self.wholePacket = self.wholePacket + pkt_S[6:]

            #if the segment is the last then print entire message
            if int(pkt_S[5]) == 1:
                print('%s: received packet "%s"' % (self, self.wholePacket))

                #reset message
                self.wholePacket = ""


       
    ## thread target for the host to keep receiving data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            #receive data arriving to the in interface
            self.udt_receive()
            #terminate
            if(self.stop):
                print (threading.currentThread().getName() + ': Ending')
                return
        


## Implements a multi-interface router described in class
class Router:
    
    ##@param name: friendly router name for debugging
    # @param intf_count: the number of input and output interfaces 
    # @param max_queue_size: max queue length (passed to Interface)
    def __init__(self, name, intf_count, max_queue_size):
        self.stop = False #for thread termination
        self.name = name
        #create a list of interfaces
        self.in_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]
        self.out_intf_L = [Interface(max_queue_size) for _ in range(intf_count)]

    ## called when printing the object
    def __str__(self):
        return 'Router_%s' % (self.name)

    ## look through the content of incoming interfaces and forward to
    # appropriate outgoing interfaces
    def forward(self):
        for i in range(len(self.in_intf_L)):
            pkt_S = None
            try:
                #get packet from interface i
                pkt_S = self.in_intf_L[i].get()
                #if packet exists make a forwarding decision
                if pkt_S is not None:
                    p = NetworkPacket.from_byte_S(pkt_S) #parse a packet out
                    # HERE you will need to implement a lookup into the 
                    # forwarding table to find the appropriate outgoing interface
                    # for now we assume the outgoing interface is also i
                    self.out_intf_L[i].put(p.to_byte_S(), True)
                    print('%s: forwarding packet "%s" from interface %d to %d with mtu %d' \
                        % (self, p, i, i, self.out_intf_L[i].mtu))
            except queue.Full:
                print('%s: packet "%s" lost on interface %d' % (self, p, i))
                pass
                
    ## thread target for the host to keep forwarding data
    def run(self):
        print (threading.currentThread().getName() + ': Starting')
        while True:
            self.forward()
            if self.stop:
                print (threading.currentThread().getName() + ': Ending')
                return 