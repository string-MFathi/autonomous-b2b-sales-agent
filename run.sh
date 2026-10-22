#!/bin/bash

echo "🚀 Starting Autonomous B2B Sales Agent Setup..."

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "env/bin/activate" ]; then
    source env/bin/activate
else
    echo "⚠️ No virtual environment found. Creating '.venv'..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

echo "📦 Installing dependencies..."
python3 -m pip install -r requirements.txt

echo "🔄 Starting the Scheduler in the background..."
nohup caffeinate -i python3 -u -m src.scheduler > scheduler_output.log 2>&1 &

sleep 2
echo "🎉 Agent is now running in the background! Use 'cat scheduler_output.log' to view logs."
