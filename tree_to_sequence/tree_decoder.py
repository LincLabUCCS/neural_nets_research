import torch
import torch.nn as nn

class TreeDecoder(nn.Module):
    """
    Decoder which produces nodes of a tree.
    """
    def __init__(self, embedding_size, hidden_size, max_num_children, nclass=32):
        """
        :param embedding_size: length of the encoded representation of a node
        :param hidden_size: hidden state size
        :param max_num_children: max. number of children a node can have
        :param nclass: number of different tokens which could be in a program
        """
        super(TreeDecoder, self).__init__()
                
        self.loss_func = nn.CrossEntropyLoss()
        
        # Linear layer to calculate log odds
        self.output_log_odds = nn.Linear(hidden_size, nclass + 1)        
        
        # Create a separate lstm for each child index
        self.lstm_list = nn.ModuleList()
        for i in range(max_num_children):
            self.lstm_list.append(nn.LSTMCell(embedding_size + hidden_size, hidden_size))
    
    
    def calculate_loss(parent, child_index, vec, true_value):
        """
        Calculate crossentropy loss from the probabilities the decoder assigns to each possible next node.
        
        :param parent: node's parent (dummy; used for compatibility with grammar decoder)
        :param child_index: index of generated child (dummy; used for compatibility with grammar decoder)
        :param vec: et vector incorporating info from the attention and hidden state of past node
        :param true_value: true value of the new node
        :returns: crossentropy loss
        """
        log_odds = self.output_log_odds(vec)
        return self.loss_func(log_odds, true_value)
        
        
    def make_prediction(self, parent, child_index, vec):
        log_odds = self.output_log_odds(vec)
        _, max_index = torch.max(log_odds, 1)
        return max_index.squeeze(0)
    
        
    def get_next(self, parent, child_index, input, hidden_state, cell_state):
        """
        Generate the hidden and cell states which will be used to generate the current node's children
        
        :param parent: node's parent (dummy; used for compatibility with grammar decoder)
        :param child_index: index of generated child (dummy; used for compatibility with grammar decoder)
        :param input: embedded reprentation of the node's parent
        :param hidden_state: hidden state generated by an lstm
        :param cell_state: cell state generated by an lstm
        """
        return self.lstm_list[child_index](input, (hidden_state, cell_state))
    
    def initialize_forget_bias(self, bias_value):
        """
        Initialize the forget bias to a certain value.  TODO: I don't actually know why this is used.  If you, future reader of this code, have knowledge of this arcane magic, please share your enlightenment with us mere mortals.
        
        :param bias_value: value the forget bias wil be set to
        """
        for lstm in self.lstm_list:
            nn.init.constant(lstm.bias_ih, bias_value)
            nn.init.constant(lstm.bias_hh, bias_value)
