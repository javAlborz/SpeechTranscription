from functions import addConventions
from functions import diarizationAndTranscription
from audio import Audio
import pyaudio
import wave
import nltk
from pydub import AudioSegment
from pydub.effects import normalize
import threading
from docx import Document
from datetime import date
import customtkinter
import matplotlib.pyplot as plt

#global variables needed to record audio
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
p = pyaudio.PyAudio()

def plotAudio(time, signal):
    plt.figure(1)
    plt.title("Audio Wave")
    plt.xlabel("Time")
    plt.plot(time, signal)
    plt.show()

class GUI:

    def recordAudio(self):
        if self.recordButton.cget("text") == 'Record':
            self.recordButton.configure(text = 'Stop')
            print("*Recording*")
            self.audio.record()
        else:
            self.recordButton.configure(text = 'Record')
            filename, time, signal = self.audio.stop()
            self.audioPlaceholder.configure(text=filename)
            plotAudio(time, signal)
            print("*Recording stopped*")
    
    def playAudio(self):
        self.audio.play()
        self.playButton.configure(text = 'Play')
    
    def pausePlayback(self):
        paused = self.audio.pause()
        labelText = "Unpause" if paused else "Pause"
        self.pauseButton.configure(text=labelText)
        
    def playbackClick(self):
        if not self.audio.playing:
            threading.Thread(target = self.playAudio).start()
            self.playButton.configure(text = 'Stop')
        else:
            self.audio.playing = False
            self.playButton.configure(text = 'Play')

    def downloadRecordedAudio(self):
        print('Downloading audio')
        
        # Create a copy of audio that is saved to computer
        download_file = customtkinter.filedialog.asksaveasfile(defaultextension = '.wav', filetypes = [("Wave File", '.wav'), ("All Files", '.*')], initialfile = "downloaded_audio.wav")
        self.audio.saveAudioFile(download_file.name)

    def uploadAudio(self):
        filename = customtkinter.filedialog.askopenfilename()
        print('File uploaded: ', filename)
        
        try:
            time, signal = self.audio.upload(filename)
            plotAudio(time, signal)
            self.audioPlaceholder.configure(text=filename)
        except wave.Error as e:
            # Handle the specific wave.Error (e.g., file not being a valid WAV file)
            print(f"Error opening file: {e}. Please ensure the file is a valid WAV file.")

    # Sends client info submitted by user to the transciption box
    def submitClientInfo(self) :
        infoEntryText = self.infoEntryBox.get()
        for i, option in enumerate(self.clientOptions):
            if self.clicked.get() == option:
                self.infoArray[i] = infoEntryText
        self.infoEntryBox.delete(0, "end")

        self.clientInfoBox.delete('1.0', "end")
        for x in range(7):
            if self.infoArray[x] != '':
                infoText = self.clientOptions[x] + ": " + self.infoArray[x] + "\n"
                self.clientInfoBox.insert("end", infoText)

    def mp3towav(self, audiofile):
        dst = self.filePath
        sound = AudioSegment.from_mp3(audiofile)
        sound.export(dst, format="wav")

    def convertToWAV(self, audioSeg):
        audioSeg.export(out_f = "converted.wav", format = "wav")

    # Runs recogtest.py (transcribes audio.wav in the current directory) then prints to the transcription box
    def transcribe(self) :
        my_progress = customtkinter.CTkProgressBar(self.master,  width = 300, mode = 'indeterminate') #creates intederminate progress bar
        my_progress.grid(row=3, column=3, padx=2, pady=2)
        my_progress.start()

        name = self.filePath.split('.')[0]
        extension = self.filePath.split('.')[1]
        if (extension == "MP3" or extension == 'mp3'):
            mp3 = AudioSegment.from_mp3(self.filePath)
            spacermilli = 2000#
            spacer = AudioSegment.silent(duration=spacermilli)#
            mp3 = spacer.append(mp3, crossfade=0)#
            ret = mp3.export("export.wav", format = "wav")
            print("Attempting to export wav from mp3. ret = " + str(ret))
        elif (extension == "wav"):
            wav = AudioSegment.from_wav(self.filePath)
            spacermilli = 2000#
            spacer = AudioSegment.silent(duration=spacermilli)#
            wav = spacer.append(wav, crossfade=0)#
            ret = wav.export("export.wav", format = "wav" )
            print("Attempting to export wav from wav. ret = " + str(ret))
        else:
            print("The format is not valid. name: " + name + " extension: " + extension)
        # create copy of file as AudioSegment for pydub normalize function
        print("File path attempting to be normalized: " + self.filePath)
        pre_normalized_audio = AudioSegment.from_file("export.wav", format = "wav")
        normalized_audio = normalize(pre_normalized_audio)
        # transcribed audio is now using normalized audiofile
        self.convertToWAV(normalized_audio)
        transcribedAudio = diarizationAndTranscription.diarizeAndTranscribe("converted.wav") #diarizing starts here
        #normal_wav.close()
        #self.transcriptionBox.configure(state='normal')

        self.transcriptionBox.configure(state='normal') #added this to see
        self.transcriptionBox.insert("end", transcribedAudio + "\n")
        print(transcribedAudio) #transcription info is right in this variable, so needs to be updated properly somewhere else
        self.transcriptionText = transcribedAudio
        self.transcriptionBox.configure(state='disabled')
        my_progress.stop() #stops progress bar
        my_progress.grid_remove() #removes progress bar



    # Adds conventions to text from transcription box and puts output in conventionBox box
    def inflectionalMorphemes(self):
        #self.conventionBox.configure(state='normal')
        converting = self.conventionBox.get("1.0", "end")
        # My name is Jake. My name are Jake. (this is a relic of debugging, DO NOT DELETE)
        converting = addConventions.addInflectionalMorphemes(converting)
        self.conventionBox.delete('1.0', "end")
        self.conventionBox.insert("end", converting)
        self.conventionBox.configure(state='disabled')

    # Sends individual sentences to addWordLevelErrors to check for correction, if there is a corrected version, add squiggles
    def grammarCheck(self):
        self.tokenizedSentences = []
        # Flag for if user wants to manually submit each sentence
        self.checkAllSentences = False
        # Configuring right-hand box, correction box, and submit button
        self.conventionBox.grid(row=5, column=4, columnspan=3)
        self.conventionBox.delete('1.0', "end")
        self.editConventionBoxButton.grid(row=7, column=5)
        self.clearConventionBoxButton.grid(row=7, column=6)
        self.correctionEntryBox.grid(row=6, column=4, columnspan=2)
        self.correctionEntryBox.delete('1.0', "end")
        self.submitCorrectionButton.grid(row=6, column=6)
        # Get raw transcription and tokenize into sentences for processing
        text = self.transcriptionText 
        # perhaps above and below is the state he was talking about, but it already gets assigned to a variable called 'text'
        self.tokenizedSentences = nltk.sent_tokenize(text)
        self.getNextCorrection()
    
    # Loops through tokenizedSentences until one needs to be corrected, sending it to correctionEntryBox
    def getNextCorrection(self):
        if (len(self.tokenizedSentences) == 0):
            # Maybe return message that all sentences were processed
            return
        while (len(self.tokenizedSentences)):
            if ((self.tokenizedSentences[0] != addConventions.correctSentence(self.tokenizedSentences[0])) or self.checkAllSentences):
                self.correctionEntryBox.insert("end", addConventions.correctSentence(self.tokenizedSentences[0]))
                del self.tokenizedSentences[0]
                break
            else:
                #self.conventionBox.configure(state='normal')
                self.conventionBox.insert("end", self.tokenizedSentences[0] + "\n")
                #self.conventionBox.configure(state='disabled')
                del self.tokenizedSentences[0]

    def applyCorrection(self):
        # Append sentence in correctionEntryBox to right-hand box
        #self.conventionBox.configure(state='normal')
        self.conventionBox.insert("end", self.correctionEntryBox.get("1.0", "end"))
       # self.conventionBox.configure(state='disabled')
        # Remove previously worked-on sentence
        self.correctionEntryBox.delete('1.0', "end")
        # Queue up the next correction for the user
        self.getNextCorrection()

    def toggleClientInfoBox(self):
        if self.infoIsVisible:
            self.clientInfoBox.grid_remove()
        else:
            self.clientInfoBox.grid(row=5, column=0)
        self.infoIsVisible = not self.infoIsVisible

    def toggleTranscriptionBox(self):
        if self.transcriptionIsVisible:
            self.transcriptionBox.grid_remove()
        else:
            self.transcriptionBox.grid(row=5, column=1, columnspan=3, padx=10, pady=10)
        self.transcriptionIsVisible = not self.transcriptionIsVisible 

    def editTranscriptionBox(self):
        if self.editTranscriptionBoxButton.cget("text") == 'Lock':
            self.editTranscriptionBoxButton.configure(text = 'Unlock')
            self.transcriptionBox.configure(state='disabled')

        else:
            self.editTranscriptionBoxButton.configure(text = 'Lock')
            self.transcriptionBox.configure(state='normal')
            
    def editConventionBox(self):
        if self.editConventionBoxButton.cget("text") ==  'Lock':
            self.editConventionBoxButton.configure(text = 'Unlock')
            self.conventionBox.configure(state='disabled')

        else:
            self.editConventionBoxButton.configure(text = 'Lock')
            self.conventionBox.configure(state='normal')

    def clearTranscriptionBox(self):
        if self.editTranscriptionBoxButton.cget("text") == 'Lock':
            self.transcriptionBox.delete('0.0', "end")
        else:
            #self.transcriptionBox.configure(state='normal')
            self.transcriptionBox.delete('0.0', "end")
            #self.transcriptionBox.configure(state='disabled')

    def clearConventionBox(self):
        if self.editConventionBoxButton.cget("text") == 'Lock':
            self.conventionBox.delete('0.0', "end")
        else:
            #self.conventionBox.configure(state='normal')
            self.conventionBox.delete('0.0', "end")
            #self.conventionBox.configure(state='disabled')

    def exportToWord(self):
        outputPath = customtkinter.filedialog.askdirectory()
        exportDocument = Document()
        text = self.transcriptionText
        exportDocument.add_paragraph(text)
        exportDocument.save(outputPath + '/' + str(date.today())+'_SALT_Transcription.docx')      

    # Creates thread that executes the transcribe function
    def transcriptionThread(self):
        th = threading.Thread(target = self.transcribe).start()

    def __init__(self):
        customtkinter.set_appearance_mode("dark")
        customtkinter.set_default_color_theme("blue")
        self.WIDTH = 1280
        self.HEIGHT = 720

        self.master = customtkinter.CTk()
        self.master.title('Speech Transcription')
        self.master.geometry(str(self.WIDTH) + 'x' + str(self.HEIGHT))
        
        self.audio = Audio(self.master)

        self.infoArray = ['','','','','','','']
        self.transcriptionText = ''


        uploadButton = customtkinter.CTkButton(self.master, text='Upload', command=lambda: self.uploadAudio())
        uploadButton.grid(row=0, column=0, padx=2, pady=2)
        self.recordButton = customtkinter.CTkButton(self.master, text='Record', command=lambda: self.recordAudio())
        self.recordButton.grid(row=0, column=1, padx=2, pady=2)

        self.audioPlaceholder = customtkinter.CTkLabel(self.master, text='(This is where the audio would be)')
        self.audioPlaceholder.grid(row=0, column=2, padx=2, pady=2)

        self.pauseButton = customtkinter.CTkButton(self.master, text='Pause', command=lambda: self.pausePlayback())
        self.pauseButton.grid(row=0, column=4, padx=2, pady=2)
        
        self.playButton = customtkinter.CTkButton(self.master, text='Play', command=lambda: self.playbackClick())
        self.playButton.grid(row=0, column=3, padx=2, pady=2)

        downloadButton = customtkinter.CTkButton(self.master, text='Download', command=lambda: self.downloadRecordedAudio())
        downloadButton.grid(row=1, column=5, padx=2, pady=2)

        transcribeButton = customtkinter.CTkButton(self.master, text='Transcribe', command=lambda:[self.transcriptionThread()])
        transcribeButton.grid(row=0, column=5, padx=2, pady=2)

        # Allows user to select a sampling attribute, type the relevant information, and submit it
        self.clientOptions = ["Name", "Age", "Gender", "Date of Birth", "Date of Sample", "Examiner Name", "Sampling Context"]
        self.clientInfo = {}
        self.clicked = customtkinter.StringVar()
        self.clicked.set("Name")
        infoDropdown = customtkinter.CTkOptionMenu(self.master, variable = self.clicked, values = self.clientOptions)
        infoDropdown.grid(row=1, column=1, padx=2, pady=2)
        self.infoEntryBox = customtkinter.CTkEntry(self.master)
        self.infoEntryBox.grid(row=1, column=2, padx=2, pady=2)
        infoSubmitButton = customtkinter.CTkButton(self.master, text="Submit", command=self.submitClientInfo)
        infoSubmitButton.grid(row=1, column=3, padx=2, pady=2)


        # LARGE BOXES AND RELATED BUTTONS
        
        # Client Information Box on the far left
        #self.clientInfoBox = customtkinter.CTkScrollableFrame(self.master, width = 100, height = 20)
        self.clientInfoBox = customtkinter.CTkTextbox(self.master, width = self.WIDTH / 5, height = self.HEIGHT / 2)
        #self.clientInfoBox.configure(state= 'disabled')
        self.clientInfoBox.grid(row=5, column=0, padx=10, pady=10)

        # Show/hide button for the box 
        self.infoIsVisible = True
        self.toggleClientInfoBoxButton = customtkinter.CTkButton(self.master, text='Toggle Table', command=self.toggleClientInfoBox)
        self.toggleClientInfoBoxButton.grid(row=6, column=0, padx=2, pady=2)

        # transcriptionBox is the left-hand box used for editing speech-recognized text
        #self.transcriptionBox = customtkinter.CTkScrollableFrame(self.master, width = 50, height = 20)
        self.transcriptionBox = customtkinter.CTkTextbox(self.master, width = self.WIDTH / 4, height = self.HEIGHT / 2)
        #self.transcriptionBox.configure(state='disabled', wrap=WORD)
        self.transcriptionBox.grid(row=5, column=1, columnspan=3, padx=10, pady=10)

        # Show/hide button for the box
        self.transcriptionIsVisible = True
        self.toggleTranscriptionBoxButton = customtkinter.CTkButton(self.master, text='Toggle Table', command=self.toggleTranscriptionBox)
        self.toggleTranscriptionBoxButton.grid(row=6, column=3, padx=2, pady=2)

        # Permits user to type in transcriptionBox
        self.editTranscriptionBoxButton = customtkinter.CTkButton(self.master, text='Unlock', command=self.editTranscriptionBox)
        self.editTranscriptionBoxButton.grid(row=6, column=1, padx=10, pady=10)
        # Clears transcriptionBox
        self.clearTranscriptionBoxButton = customtkinter.CTkButton(self.master, text='Clear', command=self.clearTranscriptionBox)
        self.clearTranscriptionBoxButton.grid(row=6, column=2, padx=10, pady=10)

        # conventionBox is the right-hand box used for adding all types of conventions
        self.conventionBox = customtkinter.CTkTextbox(self.master, width = self.WIDTH / 4, height = self.HEIGHT / 2)
        # self.conventionBox.configure(state='disabled', wrap=WORD)
        # Permits user to type in conventionBox
        self.editConventionBoxButton = customtkinter.CTkButton(self.master, text='Unlock', command=self.editConventionBox)
        # Clears conventionBox
        self.clearConventionBoxButton = customtkinter.CTkButton(self.master, text='Clear', command=self.clearConventionBox)


        # CONVENTION-RELATED BUTTONS/BOXES

        # Initiates grammarCheck process on text in transcriptionBox
        self.grammarCheckButton = customtkinter.CTkButton(self.master, text='Grammar Check', command=self.grammarCheck)
        self.grammarCheckButton.grid(row=7, column=2, padx=5, pady=2)
        # Manually edit sentences caught during grammarCheck process
        self.correctionEntryBox = customtkinter.CTkTextbox(self.master, width = self.WIDTH / 5, height = self.HEIGHT / 8) 
        #self.correctionEntryBox.configure(wrap=WORD)
        # Appends sentence within correctionEntryBox to right-hand box, continues grammarCheck process
        self.submitCorrectionButton = customtkinter.CTkButton(self.master, text='Submit', command=self.applyCorrection)
        # Applies inflectional morphemes to text in right-hand box
        self.addMorphemesButton = customtkinter.CTkButton(self.master, text='Add Morphemes', command=self.inflectionalMorphemes)
        self.addMorphemesButton.grid(row=7, column=3, padx=2, pady=2)


        # EXPORT-RELATED

        # Exports to word
        exportButton = customtkinter.CTkButton(self.master, text='Export to Word Document', command=self.exportToWord)
        exportButton.grid(row=8, column=5, padx=2, pady=2)
        # Prints
        printButton = customtkinter.CTkButton(self.master, text='Print')
        printButton.grid(row=9, column=5, padx=2, pady=2)


        self.master.mainloop()


if __name__ == "__main__":
    myGui = GUI()
