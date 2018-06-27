import torch
import torch.nn as nn

class TreeDecoderBatch(nn.Module):
    def __init__(self, embedding_size, hidden_size, max_num_children, nclass):
        """
        :param embedding_size: length of the encoded representation of a node
        :param hidden_size: hidden state size
        :param max_num_children: max. number of children a node can have
        :param nclass: number of different tokens which could be in a tree (not counting end
                       of tree token)
        """
        super(TreeDecoderBatch, self).__init__()
                
        self.cross_entropy = nn.CrossEntropyLoss(reduce=False)
        
        # Linear layer to calculate log odds. The one is to account for the eos token.
        self.output_log_odds = nn.Linear(hidden_size, nclass + 1)        
        
        # Create a separate lstm for each child index
        self.lstm_list = nn.ModuleList()
        
        self.max_num_children = max_num_children #TODO: needed?
        
        for i in range(self.max_num_children):
            self.lstm_list.append(nn.LSTMCell(embedding_size + hidden_size, hidden_size)) #TODO: Maybe just to left/right
            
    def loss_func(self, a, b):
        """
        Compute loss.
        
        Wmy does this exist?
        """
        return self.cross_entropy(a.squeeze(1), b)
    
    def calculate_loss(self, parent, child_index, et, true_value):
        """
        Calculate cross entropy loss from et.
        
        :param parent: node's parent (dummy; used for compatibility with grammar decoder)
        :param child_index: index of generated child (dummy; used for compatibility with grammar 
                            decoder)
        :param et: vector incorporating info from the attention and hidden state of past node
        :param true_value: true value of the new node
        :returns: cross entropy loss
        """
        log_odds = self.output_log_odds(et)
        return self.loss_func(log_odds, true_value)
    
    def get_next_child_states(self, parent, child_index, input, hidden_state, cell_state):
        """
        Generate the hidden and cell states which will be used to generate the current node's 
        children
        
        :param parent: node's parent (dummy; used for compatibility with grammar decoder)
        :param child_index: index of generated child 
        :param input: embedded reprentation of the node's parent
        :param hidden_state: hidden state generated by an lstm
        :param cell_state: cell state generated by an lstm
        :returns: hidden state and cell state of child node
        """
        
        hiddens = []
        cell_states = []
        for i in child_index:
            hidden, cell = self.lstm_list[i](input[i], (hidden_state[i], cell_state[i]))
            hiddens.append(hidden)
            cell_states.append(cell)
        return torch.cat(hiddens, dim=0), torch.cat(cell_states, dim=0)
    
    def initialize_forget_bias(self, bias_value):
        """
        Initialize the forget bias to a certain value. Primary purpose is that initializing
        with a largish value (like 3) tends to help convergence by preventing the model
        from forgetting too much early on.
        
        :param bias_value: value the forget bias wil be set to
        """
        for lstm in self.lstm_list:
            nn.init.constant_(lstm.bias_ih, bias_value)
            nn.init.constant_(lstm.bias_hh, bias_value)
            
    def make_prediction(self, parent, child_index, et):
        """
        Predict new child node value
        
        :param parent: parent node (dummy; used for compatibility with grammar decoder)
        :param child_index: index of generated child (dummy; used for compatibility with grammar decoder)
        :param et: attention vector of the parent
        """
        log_odds = self.output_log_odds(et)
        _, max_index = torch.max(log_odds, 1)
        return max_index