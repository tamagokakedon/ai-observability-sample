#!/bin/bash

# AI Recipe Analyzer - Run Script

echo "🍳 Starting AI Recipe Analyzer..."
echo "================================"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "Installing requirements..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found!"
    echo "Please copy .env.example to .env and configure your AWS credentials."
    echo "cp .env.example .env"
    echo ""
    echo "You can still run the application to see the setup interface."
    echo ""
fi

# Run the Streamlit application
echo "🚀 Starting Streamlit application..."
echo "Open your browser to: http://localhost:8501"
echo "Press Ctrl+C to stop the application"
echo ""

cd src && streamlit run app.py