import torch
import torch.nn as nn

class GrammarTreeDecoder(nn.Module):
    """
    Decoder which produces a tree.  It only generates child nodes which are syntactically valid.
    """
    def __init__(self, embedding_size, hidden_size, num_categories, num_possible_parents, 
                 parent_to_category, category_to_child, share_linear=False, share_lstm_cell=False):
        """
        :param embedding_size: length of the encoded representation of a node
        :param hidden_size: hidden state size
        :param num_categories: number of different output categories
        :param num_possible_parents: number of different possible parents. If you share_linear
                                     and share_lstm_cell then this becomes irrelevant.
        :param parent_to_category: function which takes in a parent node
                                   and returns the categories it can produce.
        :param category_to_child: function which takes in a category and returns 
                                  the indices of the tokens in that category.
        :param share_linear: Should the linear layers used for generating predictions be shared
                             if the category is the same or should it depend on the parent.
        :param share_lstm_cell: Should the lstm cell used to generate the hidden state be
                                shared if the category is the same or should it depend on the 
                                parent.
        """
        super(GrammarTreeDecoder, self).__init__()
        
        # Store values we'll use later
        self.parent_to_category = parent_to_category
        self.category_to_child = category_to_child
        self.share_linear = share_linear
        self.share_lstm_cell = share_lstm_cell
        
        self.loss_func = nn.CrossEntropyLoss()
        
        # The next two ModuleLists are lists of lists if you don't share.  
        # Each element in the outer list corresponds to a specific parent index.
        # Each element in the inner list corresponds to a particular category of possible 
        # next tokens (e.g. one of the EXPR tokens). If you do share they are just lists
        # corresponding to all the categories.
                
        # A list of lists of linear layers which will be used to generate predictions for a node's 
        # value.
        self.linear_lists = nn.ModuleList()
        
        if self.share_linear:
            for category in range(num_categories):
                possible_children = self.category_to_child(category)
                self.linear_lists.append(nn.Linear(hidden_size, len(possible_children)))
        else:
            for parent in range(num_possible_parents):
                self.linear_lists.append(nn.ModuleList())
                                         
                for category in self.parent_to_category(parent):
                    possible_children = self.category_to_child(category)                  
                    self.linear_lists[i].append(nn.Linear(hidden_size, len(possible_children)))

        # A list of lists of lstm_cells layers which will be used to generate the hidden states we 
        # will later use to generate a node's children.
        self.lstm_lists = nn.ModuleList()
        
        if share_lstm_cell:
            for category in range(num_categories):
                self.lstm_lists.append(nn.LSTMCell(embedding_size + hidden_size, hidden_size))
        else:
            for parent in range(num_possible_parents):
                self.lstm_lists.append(nn.ModuleList())
                                         
                for category in self.parent_to_category(parent):
                    self.lstm_lists[i].append(nn.LSTMCell(embedding_size + hidden_size, hidden_size))
                                              
        self.register_buffer('true_index', torch.LongTensor([0]))
        
    def calculate_loss(self, parent, child_index, vec, true_value):
        """
        Calculate the crossentropy loss from the probabilities the decoder assigns 
        to each syntactically valid child of a parent node.
        
        :param parent: an integer holding the value of the parent node whose child we're generating
        :param child_index: index of the child to be generated (int)
        :param vec: et vector incorporating info from the attention and hidden state of past node
        :param true_value: true value of the new node
        :returns: crossentropy loss
        """
        log_odds, possible_indices = self.get_log_odds(parent, child_index, vec)
        true_index.fill_(possible_indices.index(true_value))
        return self.loss_func(log_odds, true_index)
        
    def get_log_odds(self, parent, child_index, vec):
        """
        Calculate a score for each syntactically valid value which could be generated 
        by the given parent at the given index.
        
        :param parent: parent whose child we're generating (int)
        :param child_index: index of the child to be generated (int)
        :param vec: et vector incorporating info from the attention and hidden state of past node
        """
        category = self.parent_to_category(parent)[child_index]
        
        if self.share_linear:
            log_odds = self.linear_lists[category](et)
        else:
            log_odds = self.linear_lists[parent][category](et)
                      
        # Generate a list of possible child values
        possible_indices = self.category_to_child(parent_category_index)
        return log_odds, possible_indices
   
    def make_prediction(self, parent, child_index, vec):
        """
        Predict a token for the next node
        
        :param parent: parent of the node to be generated
        :param child_index: index of the child to be generated
        :param vec: et vector incorporating info from the attention and hidden state of past node
        """
        log_odds, possible_indices = self.get_log_odds(parent, child_index, vec)
        _, max_index = torch.max(log_odds, 1)
        return torch.LongTensor([possible_indices[int(max_index)]])
    
    def get_next(self, parent, child_index, input, hidden_state, cell_state):
        """
        Generate the hidden and cell states which will be used to generate the current node's 
        children.
        
        :param parent: parent whose child we just generated (int)
        :param child_index: index of the child we just generated (int)
        :param input: embedded reprentation of the node's parent
        :param hidden_state: hidden state generated by the parent's lstm
        :param cell_state: cell state generated by the parent's lstm
        """
        category = self.parent_to_category(parent)[child_index]
        if self.share_lstm_cell:
            return self.lstm_lists[category](input, (hidden_state, cell_state))
        else:
            return self.lstm_lists[parent][category](input, (hidden_state, cell_state))
    
    def number_children(self, parent):
        return len(self.parent_to_category(parent))
                                                   
    def initialize_forget_bias(self, bias_value):
        """
        Initialize the forget bias to a certain value. Primary purpose is that initializing
        with a largish value (like 3) tends to help convergence by preventing the model
        from forgetting too much early on.
        
        :param bias_value: value the forget bias wil be set to
        """
        for lstm_list in self.lstm_lists:
            for lstm in lstm_list:
                nn.init.constant(lstm.bias_ih, bias_value)
                nn.init.constant(lstm.bias_hh, bias_value)
