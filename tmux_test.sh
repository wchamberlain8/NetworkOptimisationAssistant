#!/bin/bash

SESSION_NAME="test"
tmux new-session -d -s $SESSION_NAME

# Rasa Shell
tmux rename-window -t $SESSION_NAME:0 "Main"
tmux send-keys -t $SESSION_NAME:0 "cd rasa && rasa shell" C-m

# Mininet
tmux split-window -v -t $SESSION_NAME:0
tmux send-keys -t $SESSION_NAME:0.1 "cd network-controller && sudo mn --switch ovsk --controller remote --custom ./topology.py --topo testTopology" C-m

# Ryu Controller
tmux split-window -h -t $SESSION_NAME:0.1
tmux send-keys -t $SESSION_NAME:0.2 "cd network-controller && ryu-manager ./controller.py" C-m

# Rasa Actions
tmux split-window -v -t $SESSION_NAME:0.2
tmux send-keys -t $SESSION_NAME:0.3 "cd rasa && rasa run actions" C-m

# Custom API
tmux split-window -h -t $SESSION_NAME:0.3
tmux send-keys -t $SESSION_NAME:0.4 "cd custom-api && uvicorn main:app --reload" C-m

tmux select-pane -t $SESSION_NAME:0.1
tmux attach-session -t $SESSION_NAME
