from typing import Optional

import numpy as np
import torch
from torch import nn

from .BaseSampler import BaseSampler


class TwoStageSampler(BaseSampler):
    def __init__(self, train_set: np.ndarray,
                 pos_weight: Optional[np.ndarray] = None,
                 neg_weight: Optional[np.ndarray] = None,
                 device: Optional[torch.device] = None,
                 batch_size: int = 256, n_neg_samples: int = 10,
                 n_neg_candidates=200):
        """ Class of Two Stage Sampler for CML.

        Args:
            train_set (np.ndarray): [description]
            pos_weight (Optional[np.ndarray], optional): [description]. Defaults to None.
            neg_weight (Optional[np.ndarray], optional): [description]. Defaults to None.
            device (Optional[torch.device], optional): [description]. Defaults to None.
            batch_size (int, optional): [description]. Defaults to 256.
            n_neg_samples (int, optional): [description]. Defaults to 10.
            n_neg_candidates (int, optional): [description]. Defaults to 200.
        """
        super().__init__(train_set, pos_weight, neg_weight,
                         device, batch_size, n_neg_samples)

        self.two_stage = True
        self.n_neg_candidates = n_neg_candidates

    def get_pos_batch(self) -> torch.Tensor:
        """ Method for positive sampling.

        Returns:
            torch.Tensor: positive batch.
        """
        batch_indices = self.pos_sampler.sample([self.batch_size])
        batch = self.train_set[batch_indices]
        return batch

    def get_and_set_candidates(self) -> torch.Tensor:
        """ Method of getting and setting candidates for 2nd stage.

        Returns:
            torch.Tensor: Indices of items of negative sample candidate.
        """
        self.candidates = self.neg_sampler.sample([self.n_neg_candidates])
        return self.candidates

    def set_candidates_weight(self, dist: torch.Tensor, dim: int):
        """ Method of calclating sampling weight for 2nd stage sampling.

        Args:
            dist (torch.Tensor) : spreadout distance (dot product) matrix, size = (n_batch, n_neg_candidates)
            dim (int): A number of dimention of embeddings.
        """
        # draw beta
        beta = torch.distributions.beta.Beta(
            (dim - 1) / 2, 1 / 2).sample([1]).to(self.device)

        # make mask
        mask = (dist > 0) * (dist < 0.99)

        # calc weight
        alpha = (1 - (dim - 1) / 2)
        log_neg_dist = torch.log(1 - torch.square(dist))  # + 1e-6)
        log_beta = torch.log(beta)
        self.candidates_weight = torch.exp(alpha * log_neg_dist + log_beta)

        # fill zero by mask
        self.candidates_weight[~mask] = 0

        # all zero -> uniform
        self.candidates_weight[self.candidates_weight.sum(axis=1) == 0] = 1

    def get_neg_batch(self) -> torch.Tensor:
        """ Method of negative sampling

        Args:
            users (torch.Tensor): indices of users in pos pairs.

        Returns:
            torch.Tensor: negative samples.
        """
        neg_candidates_indices = torch.stack([
            torch.distributions.categorical.Categorical(
                probs=self.candidates_weight[i]
            ).sample([self.n_neg_samples])
            for i in range(self.batch_size)
        ])

        neg_items = self.candidates[neg_candidates_indices]
        return neg_items
