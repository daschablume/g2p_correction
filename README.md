# forced_ui_alignment

## How to install: ##
  (was tested on Mac Mojave)
1. download this repo
2. ensure you have conda and add the conda-forge channel to your Conda configuration  
`conda config --add channels conda-forge`
3. create virtuatual environment with python>=3.9 and activate it   
`conda create -n g2p_env`
4. `conda activate g2p_env`
5. install requirements using conda
`conda install --file requirements.txt`
6. install matcha-tts using pip (which is in requirements.txt, but commented out, since conda doesn't know about its existence)
`pip install matcha-tts`
  
## How to run the app ##
1. `export FLASK_APP="YOU_ABSOLUTE_PATH/g2p_correction/g2p_correction.py"`
2. `cd YOU_ABSOLUTE_PATH/g2p_corrections`
(if you are having problems with locating your flask app within your venv, try this: 
`export FLASK_ENV=development`)
3. `flask run `

(DB is already installed and have a few entries.)
  
