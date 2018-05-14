import torch
import torch.nn as nn

from tree_to_sequence.tree_lstm import TreeLSTM
from tree_to_sequence.translating_trees import map_tree, tree_to_list

class TreeEncoder(nn.Module):
    """
    Takes in a tree where each node has a value vector and a list of children
    Produces a sequence encoding of the tree
    """
    def __init__(self, input_size, hidden_size, num_layers, valid_num_children,
                 attention=True, use_embedding=True, embedding_size=256):
        super(TreeEncoder, self).__init__()

        self.lstm_list = nn.ModuleList()
        self.use_embedding = use_embedding

        if use_embedding:
            print("EMBEDDING INPUT SIZE", input_size)
            self.embedding = nn.Embedding(input_size, embedding_size)
            self.lstm_list.append(TreeLSTM(embedding_size, hidden_size, valid_num_children))
        else:
            self.lstm_list.append(TreeLSTM(input_size, hidden_size, valid_num_children))

        # All TreeLSTMs have input of hidden_size except the first.
        for i in range(num_layers-1):
            self.lstm_list.append(TreeLSTM(hidden_size, hidden_size, valid_num_children))

        self.attention = attention

    def forward(self, tree):
        """
        Encodes nodes of a tree in the rows of a matrix.

        :param tree: a tree where each node has a value vector and a list of children
        :return a matrix where each row represents the encoded output of a single node and also
                the hidden/cell states of the root node.

        """
        if self.use_embedding:
            tree = map_tree(lambda node: self.embedding(node).squeeze(0), tree)

        hiddens = []
        cell_states = []

        for lstm in self.lstm_list:
            tree, cell_state = lstm(tree)
            hiddens.append(tree.value)
            cell_states.append(cell_state)


        hiddens = torch.stack(hiddens)
        cell_states = torch.stack(cell_states)

        if self.attention:
            annotations = torch.stack(tree_to_list(tree))
            return annotations, hiddens, cell_states
        else:
            return hiddens, cell_states

    def initialize_forget_bias(self, bias_value):
        for lstm in self.lstm_list:
            lstm.initialize_forget_bias(bias_value)