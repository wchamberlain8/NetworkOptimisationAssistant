#!/bin/bash

sudo mn -c &
wait

SESSION_NAME="test"
tmux new-session -d -s $SESSION_NAME

# Background processes - API and Rasa Actions
tmux rename-window -t $SESSION_NAME:0 "Background"
tmux send-keys -t $SESSION_NAME:0 "source /home/chambe28/typvenv/bin/activate && cd rasa && rasa run actions" C-m
tmux split-window -v -t $SESSION_NAME:0
tmux send-keys -t $SESSION_NAME:0.1 "source /home/chambe28/typvenv/bin/activate && cd custom-api && uvicorn main:app --reload" C-m

# Network processes - Mininet and Ryu Controller
tmux new-window -t $SESSION_NAME -n "Network"
tmux send-keys -t $SESSION_NAME:1 "source /home/chambe28/typvenv/bin/activate && cd network-controller && sudo mn --switch ovsk --controller remote --custom ./topology.py --topo testTopology" C-m
tmux split-window -v -t $SESSION_NAME:1
tmux send-keys -t $SESSION_NAME:1.1 "source /home/chambe28/typvenv/bin/activate && cd network-controller && ryu-manager ./controller.py" C-m

# NOA - Rasa Shell
tmux new-window -t $SESSION_NAME -n "NOA"
tmux send-keys -t $SESSION_NAME:2 "source /home/chambe28/typvenv/bin/activate && cd rasa && rasa shell" C-m

tmux select-window -t $SESSION_NAME:1
tmux select-pane -t $SESSION_NAME:1.0
tmux attach-session -t $SESSION_NAME
