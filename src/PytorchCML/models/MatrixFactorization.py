from typing import Optional

import torch
from torch import nn

from .BaseEmbeddingModel import BaseEmbeddingModel


class LogitMatrixFactorization(BaseEmbeddingModel):
    def __init__(
        self,
        n_user: int,
        n_item: int,
        n_dim: int = 20,
        max_norm: Optional[float] = None,
        max_bias: Optional[float] = 1,
        user_embedding_init: Optional[torch.Tensor] = None,
        item_embedding_init: Optional[torch.Tensor] = None,
        user_bias_init: Optional[torch.Tensor] = None,
        item_bias_init: Optional[torch.Tensor] = None,
    ):
        """
        Args :
            user_bias_init : 1d torch.Tensor size = (n_user)
            item_bias_init : 1d torch.Tensor size = (n_item)
        """

        super().__init__(
            n_user, n_item, n_dim, max_norm, user_embedding_init, item_embedding_init
        )
        self.max_bias = max_bias

        if user_bias_init is None:
            self.user_bias = nn.Embedding(n_user, 1, max_norm=max_bias)

        else:
            self.user_bias = nn.Embedding.from_pretrained(
                user_bias_init.reshape(-1, 1), max_norm=max_bias
            )
            self.user_bias.weight.requires_grad = True

        if item_bias_init is None:
            self.item_bias = nn.Embedding(n_item, 1, max_norm=max_bias)

        else:
            self.item_bias = nn.Embedding.from_pretrained(
                item_bias_init.reshape(-1, 1), max_norm=max_bias
            )
            self.item_bias.weight.requires_grad = True

    def forward(
        self, users: torch.Tensor, pos_items: torch.Tensor, neg_items: torch.Tensor
    ) -> torch.Tensor:
        """
        Args:
            users : tensor of user indices size (n_batch).
            pos_items : tensor of item indices size (n_batch, 1)
            neg_items : tensor of item indices size (n_batch, n_neg_samples)

        Returns:
            inner : inner product for each users and item pair
                   pos_pairs -> size (n_batch, 1),
                   neg_pairs -> size (n_batch, n_neg_samples)

        """

        # get enmbeddigs
        u_emb = self.user_embedding(users)  # batch_size × dim
        ip_emb = self.item_embedding(pos_items)  # batch_size × dim
        in_emb = self.item_embedding(neg_items)  # batch_size × n_samples × dim

        # get bias
        ub = self.user_bias(users)  # batch_size × 1
        ipb = self.item_bias(pos_items)  # batch_size × 1
        inb = self.item_bias(neg_items)  # batch_size × n_samples × 1

        # compute inner product
        # inner = torch.einsum('nd,njd->nj', u_emb, i_emb)

        return u_emb, ip_emb, in_emb, ub, ipb, inb

    def predict(self, pairs: torch.Tensor) -> torch.Tensor:
        """
        Args:
            pairs : tensor of indices for user and item pairs size (n_pairs, 2).
        Returns:
            inner : inner product for each users and item pair size (n_batch)
        """
        # set users and user
        users = pairs[:, 0]
        items = pairs[:, 1]

        # get enmbeddigs
        u_emb = self.user_embedding(users)  # batch_size × dim
        i_emb = self.item_embedding(items)  # batch_size × dim

        # get bias
        u_bias = self.user_bias(users)  # batch_size × 1
        i_bias = self.item_bias(items)  # batch_size × 1

        # compute distance
        inner = torch.einsum("nd,nd->n", u_emb, i_emb)

        return inner + u_bias.reshape(-1) + i_bias.reshape(-1)

    def predict_binary(self, pairs: torch.Tensor) -> torch.Tensor:
        pred = self.predict(pairs)
        sign = torch.sign(pred)
        binary = torch.uint8((sign + 1) / 2)
        return binary

    def predict_proba(self, pairs: torch.Tensor) -> torch.Tensor:
        pred = self.predict(pairs)
        proba = torch.sigmoid(pred)
        return proba
