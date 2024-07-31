# Grapheme to phoneme: correction using user interface

Powered by matcha-tts and *retrained montreal forced alignment model (*since matcha-tts is using espeak).
A part of the KTH course "Speech Technology".
Supervisors: Jens Edlund and Jim O'Regan.

## How to install and run – without Docker ##
(was tested on Mac Mojave)
#### Setup ####
1. Download/clone this repo
2. Ensure you have conda and add the conda-forge channel to your Conda configuration  
`conda config --add channels conda-forge`
3. Create virtuatual environment with python>=3.9 and activate it   
`conda create --name g2p_env python=3.10
`
4. Activate the environment
`conda activate g2p_env`
5. Install requirements using conda
`conda install --file requirements.txt`
6. Install matcha-tts using pip (which is in requirements.txt, but commented out, since conda doesn't know about its existence)
`pip install matcha-tts`
  
#### Run the app ####
1. `export FLASK_APP="YOU_ABSOLUTE_PATH/g2p_correction/g2p_correction.py"`
2. `cd YOU_ABSOLUTE_PATH/g2p_corrections`
(if you are having problems with locating your flask app within your venv, try this: 
`export FLASK_ENV=development`)
3. `flask run`

## How to install and run — with Docker ##

#### Setup ####
1. Download/clone the repository
2. Have your Docker app open
3. Being inside the `g2p_correction` directory, build the Docker image:
    ```docker build -t g2p_correction:latest .```

#### Running the app within Docker Container ####

1. Run the Docker container:
    ```
    docker run --name g2p_correction_container -p 5000:5000 --rm g2p_correction:latest
    ```

This will start the container with the environment defined in `environment.yml`.

