'''
many_arduinos.py 
Control many Arduinos from Python!
Written by Kevin Bott for UNM Social Media Workgroup, 2014.

Do-what-you-want license

kervin@unm.edu

----

Changelog

0.2.1
	Threading
		Each serial call is threaded to prevent CPU blocking
	Serial
		arduino.clear_serial_buffers() introduced to preempt serial buffer overflow
		arduino.sender() invokes arduino.clear_serial_buffers() 

0.2 
	General Housekeeping
		Less globals everywhere, data packed into dicts where possible
		More functional architechture 

	Arduino class
		has more 'self aware' serial handling
		can run in 'spoof mode' to write to stdout for non-connected, real-world 
		  development & debugging. 
		extensible & legible!

	UDP functions
		non-blocking, semi-asyncronous udp retrieval.
		UDP output (UDP server) not implemented. 

0.1 
	everything hastily implemented! let's never speak of it again!

----

Prerequisites: 

Identify arduinos in /dev; typically they appear as /dev/ttyACM[0-9]*
Check initialize_arduinos() for example

'''
import serial
import time, math, csv, random, socket, sys, thread
global arduinos_list = [None] #Holds arduino objects
global active_arduino, active_strand #outputs
global sock, udp_ip, udp_port #inputs

class arduino:
	'''
	An object to simplify and literalize how we interact with Arudinos.
	Can be invoked in 'spoof mode' to write to stdout instead of serial port
	'''
	def __init__(self, _serial_location, _number_of_strands, _spoof_mode=False):
		self.serial_location = _serial_location
		self.serial_location_string = str ( _serial_location )
		self.number_of_strands = _number_of_strands
		self.spoof_mode = _spoof_mode

	def init_serial(self):
		if self.spoof_mode == False:
			try:
				self.serial_location = serial.Serial(self.serial_location, 9600)
				#self.serial_location.nonBlocking() #uncomment for linux systems, might prevent overflowing serial buffer
				sleep(0.1)
				print self.serial_location_string, self.serial_location
			except:
				print "Could not construct serial connection ", self.return_serial_location()
		else:
			self.serial_location = sys.stdout;
			sys.stdout.write(str("  Spoof Mode Enabled\n"))
			sys.stdout.flush()

	def return_serial_buffer_length(self):
		if self.spoof_mode == False:
			return self.serial_location.outWaiting()

	def clear_serial_buffer(self, _direction):
		'''
		Flush targeted serial buffer
		'''
		if self.spoof_mode == False:
			if _direction.lower() == "in":
				self.serial_location.flushInput()
			elif _direction.lower() == "out":
				self.serial_location.flushOutput()

	def clear_serial_buffers(self):
		'''
		Check output buffer length.
		Prevents serial block. 
		'''
		if self.spoof_mode == False:
			self.serial_location.flushInput()
			self.serial_location.flushOutput()

	def send_data(self, _data, _strand, _readback=False, _transmit_pause=0.5):
		'''
		Passes data into thread-encapsulated sender function

		Anticipates dict _data and int _strand.
		_transmit_pause can be overloaded to tweak timing.
		'''
		# print "threading"
		thread.start_new_thread(self.sender, (_data, _strand, _readback, _transmit_pause) )

	def sender(self, _data, _strand, _readback=False, _transmit_pause=0.5):
		'''
		Anticipates dict _data and int _strand.
		_transmit_pause can be overloaded to tweak timing.
		'''
		#if _strand < self.return_number_of_strands():

		self.serial_location.write( "r")
		self.serial_location.write( chr( _data['red'] ))
		time.sleep(_transmit_pause)

		self.serial_location.write( "g")
		self.serial_location.write( chr( _data['green'] ))
		time.sleep(_transmit_pause)

		self.serial_location.write( "b")
		self.serial_location.write( chr( _data['blue'] ))
		time.sleep(_transmit_pause)

		self.serial_location.write( "s")
		self.serial_location.write( chr( _data['speed'] ))
		time.sleep(_transmit_pause)

		self.serial_location.write( "l")
		self.serial_location.write( chr( _data['length'] ))
		time.sleep(_transmit_pause)

		self.serial_location.write( "d")
		self.serial_location.write( chr( _strand+1 )) #strand+1 because arduino counting necessarily starts at 1

		if self.spoof_mode == True:
			self.serial_location.write("\n\n")
			self.serial_location.flush()

		if _readback == True:
			print( self.serial_location.read() )

		self.clear_serial_buffers()

	def return_serial_location(self):
		return self.serial_location_string

	def return_number_of_strands(self):
		return int( self.number_of_strands )

def initialize_arduinos(_arduinos):
	_arduinos = [
		arduino('/dev/ttyACM0', 4),
		arduino('/dev/ttyACM1', 4),
		arduino('/dev/ttyACM2', 4),
		arduino('/dev/ttyACM3', 4)
	]
	for x in range(0, ( len(_arduinos) )):
		print (_arduinos[x])
		_arduinos[x].init_serial()
	return _arduinos

def initialize_udp(_ip="0.0.0.0", _port=5005):
	'''
	Properly set up udp listener socket.
	'''
	global sock
	try:
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		sock.bind((_ip, _port))
		sock.setblocking(0)
		print "Listening at %s on port %s" % (_ip, _port)
		return True
	except:
		print "Could not create UDP socket..."
		exit(0)

def pack_values(_red=255,_green=255,_blue=0,_speed=40,_length=15):
	'''
	Pack values in standardised way.
	If no arguments are passed, default dummy values are returned
	'''
	return { 'red':_red, 'green':_green, 'blue':_blue, 'speed':_speed, 'length':_length }

def map(_num, _num_min, _num_max, _scale_min, _scale_max):
	'''
	Return given number as integer on provided scale, given its possible mins and maxes
	'''	

	num = float( _num ) 
	num_min = float( _num_min )
	num_max = float( _num_max )
	scale_min = float( _scale_min )
	scale_max = float( _scale_max )

	if num > num_max:
		num = num_max

	if num < num_min:
		num = num_min

	return int( scale_min + (scale_max - scale_min) * ( (num - num_min) / (num_max - num_min) ) )

def incoming_udp_data(_msg_length=4096):
	'''
	Retrieve, and if possible, return, UDP data
	'''
	try:
		udp_message, addr = sock.recvfrom(_msg_length) #Retrieve up to 4096 bits
		return udp_message
	except socket.error:
		return ''

def write_to_all(_r=255, _g=255, _b=255, _s=100, _l=30):
	'''
	Send data to all arduinos, as quickly as possible
	'''

	_numb_strands = 0
	for _ard in arduinos_list:
		if _numb_strands < _ard.return_number_of_strands():
			_numb_strands = _ard.return_number_of_strands()

	_ard = None
	
	for _ard in arduinos_list:
		print "arduino: ", _ard.return_serial_location()
		_ard.send_data( pack_values(_r,_g,_b,_s,_l), 4, False, 0.025 )
		time.sleep(0.075)

def main_loop( _active_arduino, _active_strand, _pause_time=1 ):
	'''
	Usual drizzle while there's no phone interaction
	'''
	global arduinos_list

	_random_num = random.random()

	#Random speed and length within range
	d_s = 25 + int( _random_num * 75 )
	d_l = 50 - int( (_random_num * 45) )

	data = pack_values(0,255,255,d_s,d_l)

	#Send data to most current strand + arduino
	print "Arduino %s and strand %s" % (_active_arduino, _active_strand+1)
	arduinos_list[_active_arduino].send_data( data, _active_strand, False, 0.05 )

	#Selects next arduino...
	#Iterates across all arduinos, strand-by-strand, i.e., 
	#arduino 1,strand 1 -> arduino N,strand 1 ; arduino1,strand 2 -> arduino N,strand 2...
	_active_arduino += 1
	_active_arduino %= len(arduinos_list)

	if (_active_arduino == 0):
		_active_strand += 1
		_active_strand %= arduinos_list[0].return_number_of_strands() 

	time.sleep(_pause_time)

	return _active_arduino, _active_strand


def response_loop( _message, _active_arduino, _active_strand ):
	'''
	Check message from phone, modify values to pack accordingly.
	This loop hijacks the main loop

	We expect values like so: 
	[c,h,l,n],[0-9]*,[0-9]*,[0-9]*

	'''

	response = _message.split(",")
	print "\n\n", response

	if len(response[3]) > 0: #If a message has been passed over UDP 

		#pre-computed color gradients: inner lists are [R,G,B]
		grad_blue_to_white = [[0,153,255], [0,191,255], [0,221,255], [0,251,255], [117,255,244], [173,255,248], [199,255,250], [219,254,255], [255,255,255]]
		grad_red_to_white = [[255,0,0], [255,81,0], [255,94,0], [255,111,0], [255,187,0], [255,238,0], [255,243,79], [255,255,219], [255,255,255]]

		#unpack UDP values
		_correct_ans = int( response[1] )
		_range = int( response[2] )
		_player_ans = int( response[3] )

		#lock lower bound of answer limit to 1. 
		#allows the phone game to have some inflexible answers, without throwing a divide-by-zero error here
		if int(_range) == 0:
			_range = 1

		#Respond to user's interaction with phone:
		if response[0].lower() == 'c':
			#Correct answer
			print "\n"
			print "correct answer"
			
			#Write white drops
			write_to_all(255,255,255,35,79)

		elif response[0].lower() == 'h':
			#Greater
			print "\n"
			print "player answer greater than correct"

			#Based on player's "correctness," select a color from the gradient list
			grad_index = map(_player_ans, _correct_ans, (_correct_ans + _range * 5), 8, 0 )
			print "mapped to ", grad_blue_to_white[grad_index]

			chosen_color = grad_blue_to_white[grad_index]
			write_to_all( chosen_color[0],chosen_color[1],chosen_color[2],35,79)
			print "\n\n"

		elif response[0].lower() == 'l':
			#Guess too low
			print "\n"
			print "player answer lower than correct"

			grad_index = map(_player_ans, (_correct_ans - _range * 5), _correct_ans, 0, 8 )
			print "mapped to ", grad_red_to_white[grad_index]

			chosen_color = grad_red_to_white[grad_index]
			write_to_all( chosen_color[0],chosen_color[1],chosen_color[2],35,79)
			print "\n\n"

	return _active_arduino, _active_strand


#Program main logic	

print( "\n\nInitializing Arduinos\n\n")
arduinos_list = initialize_arduinos( arduinos_list )

#Set start-state
active_arduino = 0
active_strand = 0

print( "\n\nSetting up UDP...")
initialize_udp()

print( "\n\nEntering main loop.")

try:
	while True:	
		latest_message = incoming_udp_data()
		if len( latest_message ) > 0:
			# Incoming text: we have something to animate.
			active_arduino, active_strand = response_loop(
				latest_message,	active_arduino, active_strand )
			time.sleep(0.2)
		else:
			# Ambient drizzle
			active_arduino, active_strand = main_loop( active_arduino, active_strand, 0.01 )
			time.sleep(0.2)
except KeyboardInterrupt:
	exit(0)