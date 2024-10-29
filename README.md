# Grapheme to phoneme: correction using user interface

Web application for Human-in-the-loop Grapeme-to-phoneme correction.
Powered by [matcha-tts](https://github.com/shivammehta25/Matcha-TTS) and retrained [Montreal Forced Aligner](https://montreal-forced-aligner.readthedocs.io/en/latest/) model.
A part of the KTH course "Speech Technology".
Supervisors: Jens Edlund and Jim O'Regan.

## How to install and run – without Docker ##
(was tested on Mac Mojave)
### Setup ###
**1. Download/clone this repo**

**2. Ensure you have conda and add the conda-forge channel to your Conda configuration**
```
conda config --add channels conda-forge
```
**3. Create virtuatual environment with python>=3.9 and activate it**
```
conda create --name g2p_env python=3.10
```
**4. Activate the environment**
```
conda activate g2p_env
```
**5. Comment out `matcha-tts` in requirements.txt** (because one can install matcha-tts package only using pip)

**6. Install requirements using conda**
```
conda install --file requirements.txt
```
**7. Install matcha-tts using pip**
```
pip install matcha-tts
```

**8. Locate your flask app** 
```
export FLASK_APP="YOU_ABSOLUTE_PATH/g2p_correction/g2p_correction.py"
```

8a. If you are having problems with locating your flask app within your venv, try this:
```
export FLASK_ENV=development
```

**9. Set up your database** 

```
cd YOU_ABSOLUTE_PATH/g2p_corrections
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### Run the app ###
```
flask run
```

## How to install and run — with Docker ##

### Setup ###
**1. Download/clone the repository**

**2. Have your Docker app open**

**3. If you don't have an ubuntu base image amongst your docker images, run this**
```
docker pull ubuntu:22.04
``` 
**4. Being inside the `g2p_correction` directory, build the Docker image:**
```
docker build -t g2p_correction:latest .
```

### Running the app within Docker Container ###

```
docker run --name g2p_correction_container -p 5000:5000 --rm g2p_correction:latest
```

