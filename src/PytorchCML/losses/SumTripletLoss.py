import torch
from torch import nn

from .BaseTripletLoss import BaseTripletLoss


class SumTripletLoss(BaseTripletLoss):
    """ Class of Triplet Loss taking sum of negative sample.
    """

    def __init__(self, margin: float = 1):
        super().__init__(margin)

    def forward(self, user_emb: torch.Tensor,
                pos_item_emb: torch.Tensor,
                neg_item_emb: torch.Tensor) -> torch.Tensor:
        """
        Args:
            user_emb : embeddings of user size (n_batch, 1, d)
            pos_item_emb : embeddings of positive item size (n_batch, 1, d)
            neg_item_emb : embeddings of negative item size (n_batch, n_neg_samples, d)

        Return:
            loss : L = Σ [m + pos_dist^2 - min(neg_dist)^2]
        """
        pos_dist = torch.cdist(user_emb, pos_item_emb)
        neg_dist = torch.cdist(user_emb, neg_item_emb)

        tripletloss = self.ReLU(self.margin + pos_dist ** 2 - neg_dist ** 2)
        loss = torch.sum(tripletloss)
        return loss
