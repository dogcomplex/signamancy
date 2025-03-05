
class Node:
    
    

def is_game_over(node):
    

def perform_one_playout(node):
    if is_game_over(node):
        node.U = get_utility_of_game_outcome(node.game_state)
    else if node.N == 0:  # New node not yet visited
        node.U = get_utility_from_neural_net(node.game_state)
    else:
        action = select_action_according_to_puct(node)
        if action not in node.children_and_edge_visits:
            new_game_state = node.game_state.play(action)
            if new_game_state.hash in nodes_by_hash:
                child = nodes_by_hash[new_game_state.hash]
                node.children_and_edge_visits[action] = (child,0)
            else:
                new_node = Node(N=0,Q=0,game_state=new_game_state)
                node.children_and_edge_visits[action] = (new_node,0)
                nodes_by_hash[new_game_state.hash] = new_node
        (child,edge_visits) = node.children_and_edge_visits[action]
        perform_one_playout(child)
        node.children_and_edge_visits[action] = (child,edge_visits+1)

    children_and_edge_visits = node.children_and_edge_visits.values()

    node.N = 1 + sum(edge_visits for (_,edge_visits) in children_and_edge_visits)
    node.Q = (1/node.N) * (
       node.U +
       sum(child.Q * edge_visits for (child,edge_visits) in children_and_edge_visits)
    )
    return