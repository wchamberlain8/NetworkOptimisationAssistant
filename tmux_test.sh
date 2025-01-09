SESSION_NAME="tmux test"
tmux new-session -d -s $SESSION_NAME

# Custom API
tmux new-window -t $SESSION_NAME:0 -n "API"
tmux send-keys -t $SESSION_NAME:0 "cd custom-api && uvicorn main:app --reload" C-m

# Mininet
tmux rename-window -t $SESSION_NAME:1 "Network-Controller"
tmux send-keys -t $SESSION_NAME:1 "cd network-controller && sudo mn --switch ovsk --controller remote --custom ./topology.py --topo testTopology" C-m

# Ryu Controller
tmux split-window -h -t $SESSION_NAME:1
tmux send-keys -t $SESSION_NAME:1.1 "cd network-controller && ryu-manager ./controller.py" C-m


#Rasa Actions
tmux new-window -t $SESSION_NAME:2 -n "Rasa-Actions"
tmux send-keys -t $SESSION_NAME:2 "cd rasa && rasa run actions" C-m

# Rasa Shell
tmux new-window -t $SESSION_NAME:3 -n "Rasa-Shell"
tmux send-keys -t $SESSION_NAME:3 "cd rasa && rasa shell" C-m

tmux attach-session -t $SESSION_NAME
