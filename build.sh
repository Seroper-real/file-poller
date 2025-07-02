#!/bin/bash

# Imposta le variabili
PYTHONPATH=src
MAIN_SCRIPT=src/main.py
DIST_DIR=dist
NAME=file-poller

echo "Building the executable..."
pyinstaller --onefile --name "$NAME" "$MAIN_SCRIPT"

echo "Cleaning up temporary files..."
rm -rf build
rm -f "$NAME.spec"

echo "Done. Check the $DIST_DIR/ folder for the $NAME executable."
#!/bin/bash

# Imposta le variabili
export PYTHONPATH=src
MAIN_SCRIPT=src/main.py
DIST_DIR=dist
NAME=file-poller

echo "Building the executable..."
pyinstaller --onefile --name "$NAME" "$MAIN_SCRIPT"

echo "Cleaning up temporary files..."
rm -rf build
rm -f "$NAME.spec"

echo "Done. Check the $DIST_DIR/ folder for the $NAME executable."
