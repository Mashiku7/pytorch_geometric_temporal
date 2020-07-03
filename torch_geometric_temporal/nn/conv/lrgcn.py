import torch
from torch.nn import Parameter
from torch_geometric.nn import RGCNConv
from torch_geometric.nn.inits import glorot, zeros


class LRGCN(torch.nn.Module):
    r"""An implementation of the Long Short Term Memory Relational
    Graph Convolution Layer. For details see this paper: `"Predicting Path
    Failure In Time-Evolving Graphs." <https://arxiv.org/abs/1905.03994>`_

    Args:
        in_channels (int): Number of input features.
        out_channels (int): Number of output features.
        num_relations (int): Number of relations.
    """
    def __init__(self, in_channels, out_channels, num_relations):
        super(LRGCN, self).__init__()

        self.in_channels = in_channels
        self.out_channels = out_channels
        self.num_relations = num_relations
        self._create_parameters_and_layers()
        self._set_parameters()


    def _create_input_gate_parameters_and_layers(self):

        self.conv_x_i = RGCNConv(in_channels=self.in_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.conv_h_i = RGCNConv(in_channels=self.out_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.w_c_i = Parameter(torch.Tensor(1, self.out_channels))
        self.b_i = Parameter(torch.Tensor(1, self.out_channels))


    def _create_forget_gate_parameters_and_layers(self):

        self.conv_x_f = RGCNConv(in_channels=self.in_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.conv_h_f = RGCNConv(in_channels=self.out_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.w_c_f = Parameter(torch.Tensor(1, self.out_channels))
        self.b_f = Parameter(torch.Tensor(1, self.out_channels))


    def _create_cell_state_parameters_and_layers(self):

        self.conv_x_c = RGCNConv(in_channels=self.in_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.conv_h_c = RGCNConv(in_channels=self.out_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.b_c = Parameter(torch.Tensor(1, self.out_channels))


    def _create_output_gate_parameters_and_layers(self):

        self.conv_x_o = RGCNConv(in_channels=self.in_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.conv_h_o = RGCNConv(in_channels=self.out_channels,
                                 out_channels=self.out_channels,
                                 num_relations=self.num_relations)

        self.w_c_o = Parameter(torch.Tensor(1, self.out_channels))
        self.b_o = Parameter(torch.Tensor(1, self.out_channels))


    def _create_parameters_and_layers(self):
        self._create_input_gate_parameters_and_layers()
        self._create_forget_gate_parameters_and_layers()
        self._create_cell_state_parameters_and_layers()
        self._create_output_gate_parameters_and_layers()


    def _set_parameters(self):
        glorot(self.w_c_i)
        glorot(self.w_c_f)
        glorot(self.w_c_o)
        zeros(self.b_i)
        zeros(self.b_f)
        zeros(self.b_c)
        zeros(self.b_o)


    def _set_hidden_state(self, X, H):
        if H is None:
            H = torch.zeros(X.shape[0], self.out_channels)
        return H


    def _set_cell_state(self, X, C):
        if C is None:
            C = torch.zeros(X.shape[0], self.out_channels)
        return C


    def _calculate_input_gate(self, X, edge_index, edge_weight, H, C):
        I = self.conv_x_i(X, edge_index, edge_weight)
        I = I + self.conv_h_i(H, edge_index, edge_weight)
        I = I + (self.w_c_i*C)
        I = I + self.b_i
        I = torch.sigmoid(I)
        return I


    def _calculate_forget_gate(self, X, edge_index, edge_weight, H, C):
        F = self.conv_x_f(X, edge_index, edge_weight)
        F = F + self.conv_h_f(H, edge_index, edge_weight)
        F = F + (self.w_c_f*C)
        F = F + self.b_f
        F = torch.sigmoid(F)
        return F


    def _calculate_cell_state(self, X, edge_index, edge_weight, H, C, I, F):
        T = self.conv_x_c(X, edge_index, edge_weight)
        T = T + self.conv_h_c(H, edge_index, edge_weight)
        T = T + self.b_c
        T = torch.tanh(T)
        C = F*C + I*T
        return C

    def _calculate_output_gate(self, X, edge_index, edge_weight, H, C):
        O = self.conv_x_o(X, edge_index, edge_weight)
        O = O + self.conv_h_o(H, edge_index, edge_weight)
        O = O + (self.w_c_o*C)
        O = O + self.b_o
        O = torch.sigmoid(O)
        return O


    def _calculate_hidden_state(self, O, C):
        H = O * torch.tanh(C)
        return H


    def forward(self, X, edge_index, edge_type, H=None, C=None):
        """
        Making a forward pass. If edge weights are not present the forward pass
        defaults to an unweighted graph. If the hidden state and cell state
        matrices are not present when the forward pass is called these are
        initialized with zeros.

        Arg types:
            * **X** *(PyTorch Float Tensor)* - Node features.
            * **edge_index** *(PyTorch Long Tensor)* - Graph edge indices.
            * **edge_type** *(PyTorch Long Tensor)* - Edge weight vector (optional).
            * **H** *(PyTorch Float Tensor)* - Hidden state matrix for all nodes (optional).
            * **C** *(PyTorch Float Tensor)* - Cell state matrix for all nodes (optional).

        Return types:
            * **H** *(PyTorch Float Tensor)* - Hidden state matrix for all nodes.
            * **C** *(PyTorch Float Tensor)* - Cell state matrix for all nodes.
        """
        H = self._set_hidden_state(X, H)
        C = self._set_cell_state(X, C)
        I = self._calculate_input_gate(X, edge_index, edge_type, H, C)
        F = self._calculate_forget_gate(X, edge_index, edge_type, H, C)
        C = self._calculate_cell_state(X, edge_index, edge_type, H, C, I, F)
        O = self._calculate_output_gate(X, edge_index, edge_type, H, C)
        H = self._calculate_hidden_state(O, C)
        return H, C
