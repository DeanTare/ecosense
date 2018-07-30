# DEAN'S VERSION

# Import Python libraries
import sys
import picamera
import pyaudio
import serial
import collections
import time
import wave
import csv
import socket
import base64
import thread
from Tkinter import *
from PIL import ImageTk, Image
import tkFont

host = sys.argv[1]
mode = sys.argv[2]

win = Tk()
win.title("EcoSense")
win.geometry("800x480")
#myFont = tkFont.Font(family='Helvetica', size=48, weight='bold')
#stringVar = StringVar()
#stringVar.set("\n\n<Connect to EcoBrain>")
#labelText = Label(win, textvariable=stringVar, font=myFont)
path = "gui/insert.jpg"
gui = ImageTk.PhotoImage(Image.open(path))
panel = Label(win, image=gui)
panel.image = gui
panel.pack()

def updateLabel(txt): # you may have to use *args in some cases
    stringVar.set(txt)

def updatePanel(path):
	gui = ImageTk.PhotoImage(Image.open(path))
	panel.configure(image=gui)
	panel.image = gui

updatePanel("gui/logo.jpg")
win.update()

# States
CLASSIFIED = 0
SENSING = 1
DETECTED = 2
IDENTIFYING = 3

# Define constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
CHUNK = 512
DURATION = 2
RESOLUTION = 0.1
FREQ = "r"
MASS = "a"
ZERO = "z"
TARE = "s"
SENSITIVITY = 22	# Detection sensitivity
OFFSET = 0.5		# Offset for recording
RESET = 0.75

PORT = 8888

print(" ")
print("------------------")
print(" PYAUDIO WARNINGS ")
print("------------------")

arduino = serial.Serial('/dev/ttyACM0', 9600)
microphone = pyaudio.PyAudio()

mass_buff = collections.deque(maxlen = DURATION/RESOLUTION)
freq_buff = collections.deque(maxlen = DURATION/RESOLUTION)
sound_buff = collections.deque(maxlen = RATE/CHUNK*DURATION)

print("---------------------")

def Record():
	stream = microphone.open(format=FORMAT,
							 channels=CHANNELS,
							 rate=RATE,
							 input=True,
							 frames_per_buffer=CHUNK)
	#global sound_buff
	while True:
		data = stream.read(CHUNK, exception_on_overflow = False)
		sound_buff.append(data)

def connect():
	#host = raw_input("Enter Server IP: ")
	print " "
	print "Attempting to connect to " + host
	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect((host, PORT))
	print 'Connected to EcoBrain'
	#print " "
	return s

def disconnect(s):
	print "Closing connection."
	print " "
	s.close()

def sendMessage(s, string):
	bytestr = str(string)
	bytestrlen = str(len(bytestr))
	#print "Sending " + bytestrlen + " bytes."
	s.send(bytestrlen.encode())
	status = s.recv(1).decode()
	if status == "0":
		print "Error: Length not received."
		return
	s.send(bytestr.encode())
	status = s.recv(1).decode()
	if status == "0":
		print "Error: Data not received."
		return

#print " "
s = connect()

#mode = raw_input("Mode (collect/predict): ")
if mode == "c":
	mode = "collect"
elif mode == "p":
	mode = "predict"

sendMessage(s, mode)

if mode == "collect":
	label = raw_input("Label (plastic/metal/glass/paper): ")
	sendMessage(s, label)

#updateLabel("\n\n<Insert Item>")
updatePanel("gui/insert.jpg")
win.update()

# Instantiate load cell and metal detector
arduino.write(ZERO)
arduino.write(TARE)

#p = Process(target = Record)
#p.start()
thread.start_new_thread(Record,())

print " "
print "===================="
print " ECOSENSE INITIATED "
print "===================="
print " "

if mode == "collect":
	print "Collection mode enabled."
else:
	print "Prediction mode enabled."

state = SENSING
print " "
print "Sensing..."
mass_prev = 0

# Main loop
while True:
	if state == CLASSIFIED:
		arduino.write(MASS)
		mass_new = float(arduino.readline())
		diff = (mass_new-mass_prev)/RESOLUTION
		if diff < -SENSITIVITY:
			time.sleep(RESET)
			arduino.write(ZERO)
			arduino.write(TARE)
			state = SENSING
			print " "
			print "Sensing..."
			#updateLabel("\n\n<Insert Item>")
			updatePanel("gui/insert.jpg")
			win.update()


	if state == SENSING:
		start = time.time()
		arduino.write(MASS)
		mass_new = float(arduino.readline())
		arduino.write(FREQ)
		freq_new = float(arduino.readline())
		mass_buff.append(mass_new)
		freq_buff.append(freq_new)
		diff = (mass_new-mass_prev)/RESOLUTION
		mass_prev = mass_new
		end = time.time()
		sleep = RESOLUTION-(end-start)
		if sleep < 0:
			sleep = 0
		time.sleep(sleep)
		if diff > SENSITIVITY:
			state = DETECTED
			count = (DURATION-OFFSET)/RESOLUTION
			print " "
			print "Detected!"
			#updateLabel("\n\nProcessing...")
			updatePanel("gui/process.jpg")
			win.update()
			start = time.time()

	if state == DETECTED:
		arduino.write(MASS)
		mass_new = float(arduino.readline())
		arduino.write(FREQ)
		freq_new = float(arduino.readline())
		mass_buff.append(mass_new)
		freq_buff.append(freq_new)
		count = count - 1
		if count < 0:
			state = IDENTIFYING
			print " "
			if mode == "collect":
				print "Collecting..."
			else:
				print "Identifying..."


	if state == IDENTIFYING:
		if len(list(freq_buff)) < DURATION/RESOLUTION:
			count = count + 1
			state = DETECTED
			pass
		sound_list = list(sound_buff)
		#stream.stop_stream()
		#stream.close()
		# Make WAV
		wf = wave.open('sound.wav', 'wb')
		wf.setnchannels(CHANNELS)
		wf.setsampwidth(microphone.get_sample_size(FORMAT))
		wf.setframerate(RATE)
		wf.writeframes(b''.join(sound_list))
		wf.close()
		print "Sound recorded."
		# Make CSV
		csvfile = open('series.csv', 'wb')
		fieldnames = ['Time', 'Freq', 'Mass']
		writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
		writer.writeheader()
		for i in range(int(DURATION/RESOLUTION)):
			writer.writerow({'Time': i*RESOLUTION, 'Freq': list(freq_buff)[i], 'Mass': list(mass_buff)[i]})
		csvfile.close()
		print "Series recorded."
		# Make JPG
		camera = picamera.PiCamera()
		camera.capture("image.jpg")
		camera.close()
		print "Image captured."
		 # Send JPG
		form = "jpg"
		sendMessage(s, form)
		with open ("image.jpg", "rb") as f:
			data = base64.b64encode(f.read())
		sendMessage(s, data)
		print "Sent 'image.jpg'"
		# Send WAV
		form = "wav"
		sendMessage(s, form)
		with open ("sound.wav", "rb") as f:
			data = base64.b64encode(f.read())
		sendMessage(s, data)
		print "Sent 'sound.wav'"
		# Send CSV
		form = "csv"
		sendMessage(s, form)
		with open ("series.csv", "rb") as f:
			data = base64.b64encode(f.read())
		sendMessage(s, data)
		print "Sent 'series.csv'"

		print " "
		if mode == "collect":
			print "Sample collected!"
		else:
			vote = s.recv(16).decode()
			#print vote, "identified!"
			#updateLabel("\n\n" + vote)
			#win.update()
			print "Vote:", vote
			if vote == "Plastic":
				updatePanel("gui/plastic.jpg")
			elif vote == "Metal":
				updatePanel("gui/metal.jpg")
			elif vote == "Glass":
				updatePanel("gui/glass.jpg")
			else:
				updatePanel("gui/landfill.jpg")	
			win.update()
			end = time.time()
			print "Time:", end-start
		arduino.write(MASS)
		mass_prev = float(arduino.readline())
		mass_buff.clear()
		freq_buff.clear()
		state = CLASSIFIED
		

