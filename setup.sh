#!/bin/bash
echo "Setting up Python virtual environment..."
python -m venv venv

echo "Activating virtual environment..."
# Note: For Windows, the user will need to run venv\Scripts\activate
source venv/Scripts/activate 2>/dev/null || source venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete! Run 'source venv/bin/activate' or 'venv\\Scripts\\activate' (Windows) to activate."
