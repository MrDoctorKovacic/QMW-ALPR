# Python 2.7
from openalpr import Alpr
import sys
import sqlite3 # for both portable and I/O sensitive record keeping
import json
import os.path
import urllib
import time

DEBUG_PRINT = True
CREATE_NEW_DB = False

if(not os.path.isfile('alprRecords.db')): CREATE_NEW_DB = True
conn = sqlite3.connect('alprRecords.db')
c = conn.cursor()

def createTable():
    # Create table
    c.execute('''CREATE TABLE alpr (time int, records text, camera int)''')
    conn.commit()

def insertRow(time, records, camera):
    c.execute("INSERT INTO alpr VALUES ('{}','{}',{})".format(time, records, camera))
    conn.commit()

if __name__ == "__main__":
    # Create table if the file didn't exist
    if(CREATE_NEW_DB): createTable()

    # Set up image recognition
    alpr = Alpr("us", "/etc/openalpr/openalpr.conf", "/usr/share/openalpr/runtime_data/")
    if not alpr.is_loaded():
        print("Error loading OpenALPR")
        sys.exit(1)
    
    alpr.set_top_n(20)
    alpr.set_default_region("ca")

    # Begin ALPR
    currentCamera = 0 # 0 = L, 1 = R
    while True:
        # Timestamp for consistient record keeping
        currentTime = int(time.time())

        # File to be saved (possibly temporarily) for alpr
        alprImage = "./images/camera{}-{}.jpg".format(currentCamera, currentTime)

        # Save image from camera
        urllib.urlretrieve("http://localhost:808{}/?action=snapshot".format(currentCamera), alprImage)

        # Parse image into results
        results = alpr.recognize_file(alprImage)
        results_json = json.dumps(results)

        # Save if a match otherwise delete image
        if(results["results"]):
            insertRow(currentTime, results_json, currentCamera)

            if(DEBUG_PRINT):
                print("Found plate: {}".format(results["results"][0]["plate"]))
        else:
            os.remove(alprImage)
        
        # Flip bit to other camera
        currentCamera = 1-currentCamera

        # Wait a bit
        time.sleep(1)

    # Call when completely done to release memory
    alpr.unload()
