# forced_ui_alignment


1. How to install:
  (was tested on Mac Mojave)

  0) download this repo
  1) ensure you have conda and add the conda-forge channel to your Conda configuration
    conda config --add channels conda-forge
  2) create virtuatual environment with python>=3.9 and activate it
      conda create -n g2p_env
  3) conda activate g2p_env
  4) install requirements using conda
     conda install --file requirements.txt
  5) export FLASK_APP="YOU_ABSOLUTE_PATH/g2p_correction/g2p_correction.py"
  4) cd YOU_ABSOLUTE_PATH/g2p_correction
  6) flask run
  
  (if you are having problems with locating your flask app within your venv,
   try this: 
    export FLASK_ENV=development)

2. How to create your local db:

  0) cd YOU_ABSOLUTE_PATH/g2p_correction
  1) flask db init
  2) flask db migrate -m "tables"
  3) flask db upgrade

