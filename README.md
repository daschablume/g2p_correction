# forced_ui_alignment

1. Requirements are in requirements.txt

3. How to install:

  0) pull this repo
  1) create virtuatual environment with python>=3.9 and activate it
  2) run this command there
     python3 -m pip install -r requirements.txt
  3) FLASK_APP="YOU_ABSOLUTE_PATH/g2p_correction/g2p_correction.py"
     export FLASK_APP
  4) cd YOU_ABSOLUTE_PATH/g2p_correction
  6) flask run
  
  (if you are having problems with locating your flask app within your venv,
   try this: 
    export FLASK_ENV=development)

3. How to create your local db:

  0) cd YOU_ABSOLUTE_PATH/g2p_correction
  1) flask db init
  2) flask db migrate -m "tables"
  3) flask db upgrade

4. CREATE BRANCH BEFORE ANY CHANGES

