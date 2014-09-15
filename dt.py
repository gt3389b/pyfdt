#! /usr/bin/env python

#  .-------------------------------------------------------------------------.
#  |                                                                         |
#  |                  Flattened Device Tree                                  |
#  |                                                                         |
#  | Author:  Russell Leake (leaker@cisco.com)                               |
#  |                                                                         |
#  '-------------------------------------------------------------------------'
# Libraries
#from cisco_packaging import utilities
import argparse, json, logging, os, re, struct, sys
from ordered_set import *

def get_uint(data_s):
   data = data_s['data']
   offset = data_s['offset']
   data_s['offset'] += 4
   return struct.unpack(">I",data[offset:offset+4])[0]

def get_bytes(data_s, length):
   data = data_s['data']
   offset = data_s['offset']
   data_s['offset'] += length
   return data[offset:offset+length]

def process_data_block(root, data_s, offset_list, string_list):
   """
   """
   while 1:
      token = get_uint(data_s)
      if token == 0x1:     # FDT_BEGIN_NODE
         node=dict()
         tStr = ""
         while 1:
            value = get_bytes(data_s, 4)
            tStr += str(value)
            if '\0' in value:
               node_name=tStr.strip('\0')
               break

         # special case for root node
         if node_name == "":
            node_name = "/"

         # recursively call to child nodes
         process_data_block(node, data_s, offset_list, string_list)
         # now store node in dictionary
         root[node_name]=node

      elif token == 0x3:     # FDT_PROP
         length = get_uint(data_s)
         alength = (length + 3) & ~3
         name_offset = get_uint(data_s)

         if name_offset in offset_list:
            name=string_list[offset_list.index(name_offset)].strip('\0')
         else:
            for i,offset in enumerate(offset_list):
               if name_offset < offset:
                  name=string_list[offset_list.index(offset_list[i-1])][name_offset-offset+1:].strip('\0')
                  break

         if length:
            value = get_bytes(data_s, alength)

            # test to see if the value is printable.  There is no better way to determine if
            # the value is an int or string
            printable = False
            if value[length-1] == '\0':
               if value[0] != '\0':
                  if False not in set(((ord(c) in range(32,127)) | (c=='\0')) for c in iter(value)):
                     printable = True

            if printable:
               value=value.strip('\0')
            elif not (length % 4):
               # rewind
               data_s['offset'] -= alength
               value=[get_uint(data_s) for c in range(0,length/4)]
               if len(value) == 1:
                  value=value[0]
            else:
               data_s['offset'] -= alength
               value=map(ord, get_bytes(data_s, alength)[:length])
            root[name]=value
         else:
            root[name]=True

            
      elif token == 0x2:     # FDT_END_NODE
         #print " "*k*3+"}"
         return
      elif token == 0x9:     # FDT_END
         return
      elif token == 0x4:     # FDT_NOP
         print "FDT_NOP"
         pass
      else:
         print "unknown token: %08x" % token
         break


class Node:
   FDT_MAGIC=0xd00dfeed
   FDT_BEGIN_NODE=0x1
   FDT_END_NODE=0x2
   FDT_PROP=0x3
   FDT_NOP=0x4
   FDT_END=0x9


   def __init__(self, name=None):
      self.name = name
      self.properties={}
      self.nodes=list()
      print "Node name: ",self.name

   def add_property(self, key, value):
      """ simply add a property to the node property dictionary """
      self.properties[key]=value
      #print "%s: add_property %s " % (self.name, key)

   def add_node(self, node):
      #print " to node " + self.name
      #print "  "+"".join(["%02x" % b for b in node])
      self.nodes.append(node)
      
   def toBin(self, add_to_stringpool):
      body = bytearray()
      body.extend(struct.pack(">I",Node.FDT_BEGIN_NODE))   

      # add the node name padded by null terminators
      body.extend(struct.pack(str((len(self.name)+1+3)&~0x3)+'s',self.name))

      for key in self.properties:
         val = self.properties[key]
         #print key, val
         body.extend(struct.pack(">I",Node.FDT_PROP))   
         offset=add_to_stringpool(key)
         if isinstance(val, int):
            body.extend(struct.pack(">I",4))                            # len
            body.extend(struct.pack(">I",offset))                       # offset
            body.extend(struct.pack('>I',val))                          # integer
         elif isinstance(val, str):
            body.extend(struct.pack(">I",len(val)+1))                   # len
            body.extend(struct.pack(">I",offset))                       # offset
            body.extend(struct.pack(str((len(val)+1+3)&~0x3)+'s',val))  # string
         elif isinstance(val, list):
            unaligned_len=len(val)
            aligned_len=(len(val)+3)&~0x3
            if(val[0] > 255):
               body.extend(struct.pack(">I",unaligned_len*4))              # len
               body.extend(struct.pack(">I",offset))                       # offset
               for i in range(0,unaligned_len):
                  body.extend(struct.pack(">I",val[i]))                      
            else:
               body.extend(struct.pack(">I",unaligned_len))                # len
               body.extend(struct.pack(">I",offset))                       # offset
               for i in range(0,unaligned_len):
                  body.extend(struct.pack(">B",val[i]))                      
               for i in range(0,aligned_len - unaligned_len):
                  body.extend(struct.pack(">B",0)) 
         else: 
            raise(Exception("Unsupported type"));

      for node in self.nodes:
         body.extend(node)

      body.extend(struct.pack(">I",Node.FDT_END_NODE))   
      return body

class DeviceTree:
   FDT_BEGIN_NODE=0x1
   FDT_END_NODE=0x2
   FDT_PROP=0x3
   FDT_END=0x9
   FDT_NOP=0x4

   def __init__(self, filename=None):
      if filename:
         self.open(filename)
      #self.string_pool = []
      self.string_pool = OrderedSet()

   def open(self, filename):
      with open(args.input) as f:
         data_s = {}

         data_s['data'] = f.read()
         data_s['offset'] = 0

         magic = get_uint(data_s)
         if (magic != 0xd00dfeed):
            raise Exception("magic failed")

         self.total_size = get_uint(data_s)
         self.off_dt_struct = get_uint(data_s)
         self.off_dt_strings = get_uint(data_s)
         self.off_mem_rsvmap = get_uint(data_s)
         self.version = get_uint(data_s)
         self.last_version = get_uint(data_s)

         f.seek(self.off_dt_struct)
         data_s['data'] = f.read()
         data_s['offset'] = 0

         f.seek(self.off_dt_strings)
         strings = f.read()

         offset_list=[match.start()+1 for match in re.finditer(re.escape('\0'), strings)]
         string_list=strings.split('\0')
         offset_list.insert(0, 0)

         # build our structure
         self.dt_struct={}
         process_data_block(self.dt_struct, data_s, offset_list, string_list)

   def walk(self, name, node):
      """ Recursively walk a dictionary creating DT Nodes and adding the properties
      """
      n=Node(name)

      for key, prop in node.items():
         if isinstance(prop, dict):
            n.add_node(self.walk(key, prop))
         else:
            #print key, prop
            n.add_property(key,prop)

      return n.toBin(self.add_to_stringpool)

   def add_to_stringpool(self, string):
      """ Adds a string to the string pool and returns its byte offset in the stringpool 
          NOTE:  Once a string has been placed in the string pool, it can't be moved or removed else
                 all offsets will be incorrect 
      """
      self.string_pool.add(string)

      return ('\0'.join(self.string_pool)+'\0').find(string)

   def get_stringpool(self):
      """ Return the string pool as concatenated, null-terminated strings """
      return '\0'.join(self.string_pool)+'\0'


   def processNodes(self):
      return self.walk("/", self.dt_struct['/'])
      #return bytearray()

   def toBin(self):
      body = self.processNodes()
      body.extend(struct.pack(">I",Node.FDT_END)) 

      string_pool = self.get_stringpool()

      # now the we've constructed the dt_structure, we can create the header

      # get the length of the dt_struct
      size_dt_struct = len(body)
      size_dt_strings = len(string_pool)

      off_mem_rsvmap = 0x28
      off_dt_struct = off_mem_rsvmap + 0x10
      last_version = 0x10
      version = 0x11

      header = bytearray()
      header.extend(struct.pack(">I",Node.FDT_MAGIC))                                     # magic
      header.extend(struct.pack(">I",off_dt_struct + size_dt_struct + size_dt_strings))   # size
      header.extend(struct.pack(">I",off_dt_struct))                                      # off_dt_struct
      header.extend(struct.pack(">I",size_dt_struct + off_dt_struct))                     # off_dt_strings
      header.extend(struct.pack(">I",off_mem_rsvmap))                                     # off_mem_rsvmap
      header.extend(struct.pack(">I",version))                                            # version
      header.extend(struct.pack(">I",last_version))                                       # last_version
      header.extend(struct.pack(">I",0))                                                  # boot_cpuid_phys
      header.extend(struct.pack(">I",size_dt_strings))                                    # size_dt_strings
      header.extend(struct.pack(">I",size_dt_struct))                                     # size_dt_struct
      header.extend(struct.pack(">I",0))                                                  # mem_rsvmap
      header.extend(struct.pack(">I",0))                                                  # mem_rsvmap
      header.extend(struct.pack(">I",0))                                                  # mem_rsvmap
      header.extend(struct.pack(">I",0))                                                  # mem_rsvmap

      # now append the dt_struct
      header.extend(body)

      # now append the dt_strings
      header.extend(struct.pack(str(len(string_pool))+'s',string_pool))

      return header

   def save(self):
      self.walk(self.dt_struct)

   def __str__(self):
      return json.dumps(self.dt_struct, indent=3, sort_keys=True)

   def __repr__(self):
      return bytes(self.toBin())

# Test out complex decorator
logger = logging.getLogger('manifest')
#logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(asctime)s %(name)s Line: %(lineno)d |  %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__=='__main__':
   parser = argparse.ArgumentParser(description='Process commandline arguments')
   parser.add_argument("-i", "--input", dest="input", help="Input filename", metavar="INPUT")
   parser.add_argument("-q", "--quiet", action="store_false", dest="verbose", default=True, help="Don't print status messages to stdout")

   args = parser.parse_args()

   if args.verbose == True:
      logger.setLevel(logging.DEBUG)

   if not args.input:
      parser.print_help()
      sys.exit(1)

   x = DeviceTree(filename=args.input)
   print x
   print ""
   f = open('output', 'wb')
   f.write(x.__repr__())
   f.close()

   #x = Node("test1")
   #print x.__repr__()
   #x.add_property("timestamp",0x53cbcc8b)
   #x.add_property("description","Various kernels, ramdisks and FDT blobs")
   #x.add_property("#address-cells",0x00000001)
   #print x.__repr__()
   #f = open('output', 'wb')
   #f.write(x.__repr__())
   #f.close()
