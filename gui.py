from Tkinter import *
from PIL import ImageTk, Image
import tkFont
import os

win = Tk()
win.title("EcoSense")
win.geometry("800x480")

load = Image.open("image.jpg")
logo = ImageTk.PhotoImage(load)
myFont = tkFont.Font(family='Helvetica', size=24, weight='bold')

def exitProgram():
	print("Exit Button pressed")
	win.quit()

labelText = Label(win, text="\n\n\n<Insert Item>", font=myFont)
labelText.pack()

#logoPanel = Label(win, image=logo)
#logoPanel.image = logo
#ogoPanel.pack()
#logoPanel.pack(side=BOTTOM, fill="both", expand="yes")

exitButton = Button(win, text = "Exit", font = myFont, command = exitProgram, height = 2, width = 6)
exitButton.pack(side = BOTTOM)

mainloop()