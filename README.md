# Low-cost BCI for upper-limb motor imagery detection

## Description
Brain-machine interfaces (BMIs) can be very useful for physically-impaired users.
Upper-limb motor imagery BMIs can be used to, for example, control movements of a robotic arm. 
In this project, open loop (data collection) as well as closed loop (real-time) experiments were done using a low-cost EEG device.
In the end, user could play a game of Space Invaders in real-time using upper-limb motor imagery.

## Installation instructions
```
# Create a virtual environment:
conda create --name BCI --python=3.9
conda activate BCI
# Install src to run scripts in src folder:
pip install -e .
# Install required packages:
pip install -r requirements.txt

# For running experiments with psychopy with data collection using pylsl:
conda install -c conda-forge psychopy
pip install pylsl
```

## Usage instruction
All scripts for open loop are visible in the scripts folder.
Scripts can be ran by using the command line, as example for pre-processing of subject X01 for CSP pipeline:
```
python scripts/openloop_datacollect/1_pre.py --subjects X01 --pline csp
```
Note that for above scripts, a data folder is needed, creating by running experiments or download data.
Please check if the path is correct.
Open loop scripts are found in 'openloop_datacollect'.
Closed loop scripts are found in 'realtime_exp'.

## Additional usage instruction 
BCI hardware setup: https://www.youtube.com/watch?v=UVVUJTwvGnw&list=PL_JwSzOwEdQQWf17SrATPC6GnzgVjmHT&index=65

Connect to BCI: https://www.youtube.com/watch?v=LOfIr2F7-Tc&list=PL_JwSzOwEdQQWf17SrATPC6GnzgVjmHT&index=66  

Open Unicorn Bandpower in Unicorn Suite and wait until all dots are green. Experiment a little with 
blinking and clicking teeth to see muscle artifacts. Try lifting your arms and see how the signal changes. 
Try the same thing, but this time just using your imagination to get a feel for it. Close the Unicorn Bandpower application. 

Open Unicorn LSL in DevTools. Open UnicornLSL.exe in the directory that opens. Tap "Open" and "Start". 
(see video tutorial: https://www.youtube.com/watch?v=l18lJ7MGU38&list=PL_JwSzOwEdQQWf17SrATPC6GnzgVjmHT&index=61)

Open the project in VS Code:
1. Start getting used to the experimental setup in 1_practice. 
2. Record data with 3_ol (don't forget to adjust the subject name). 
3. Preprocess with 4_pre 
4. Fine tune with 5_ft 
5. Practice your ability to send a signal with 6_cl and see if the model predicts correctly (dot moves in the correct direction).
6. Play the game with 7a_game 

If you want to get information about the accuracy of the models, go to openloop scripts (run them in order from 1 to 6, 
links are adapted to get data you recorded with 3_ol) 

Have fun! 